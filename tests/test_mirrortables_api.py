import unittest

from connects_neuvue.mirrortables.api import (
    DATASET_SCHEMAS,
    DEFAULT_HOST,
    MirrorTableAPI,
    create_virtual_module,
    schema_name_from_dataset,
)


class FakeRelation:
    class Heading:
        primary_key = ("segment_id", "split_index")

    heading = Heading()

    def __and__(self, restriction):
        self.restriction = restriction
        return self

    def fetch(self, *attributes, **kwargs):
        return {
            "attributes": attributes,
            "format": kwargs.get("format"),
        }

    def fetch1(self, attribute):
        values = {
            "neuron_skeleton": "fake-skeleton",
            "axon_skeleton": "fake-axon-skeleton",
            "neuron_graph": "fake-graph-path",
        }
        return values[attribute]


class AutoProofreadNeuron(FakeRelation):
    pass


class AutoProofreadNeuronObj(FakeRelation):
    pass


class AutoProofreadNeuronErrorStats(FakeRelation):
    pass


class AutoProofreadNeuronSynapse(FakeRelation):
    pass


class AutoProofreadNeuronSynapseErrors(FakeRelation):
    pass


AutoProofreadNeuron.Obj = AutoProofreadNeuronObj
AutoProofreadNeuron.ErrorStats = AutoProofreadNeuronErrorStats
AutoProofreadNeuron.Synapse = AutoProofreadNeuronSynapse
AutoProofreadNeuron.SynapseErrors = AutoProofreadNeuronSynapseErrors


class DecimatedMesh(FakeRelation):
    pass


class DecimatedMeshObj(FakeRelation):
    pass


DecimatedMesh.Obj = DecimatedMeshObj


class DecompositionCelltype(FakeRelation):
    pass


class DecompositionCelltypeObj(FakeRelation):
    pass


DecompositionCelltype.Obj = DecompositionCelltypeObj


class FakeVirtualModule:
    AutoProofreadNeuron = AutoProofreadNeuron
    DecimatedMesh = DecimatedMesh
    DecompositionCelltype = DecompositionCelltype


class FakeDataJoint:
    def __init__(self):
        self.config = {}
        self.connected = False
        self.virtual_modules = []

    def conn(self):
        self.connected = True

    def VirtualModule(self, module_name, schema_name, add_objects=None):
        self.virtual_modules.append((module_name, schema_name))
        return FakeVirtualModule()


class MirrorTableAPITest(unittest.TestCase):
    def test_schema_name_from_dataset(self):
        self.assertEqual(DATASET_SCHEMAS["minnie35"], "minnie35_mirrortables")
        self.assertEqual(schema_name_from_dataset("v1dd"), "v1dd_mirrortables")
        with self.assertRaises(ValueError):
            schema_name_from_dataset("unknown")

    def test_create_virtual_module_uses_dataset_schema(self):
        dj = FakeDataJoint()
        module = create_virtual_module("minnie35", datajoint_module=dj)
        self.assertIsInstance(module, FakeVirtualModule)
        self.assertEqual(dj.virtual_modules, [("minnie35", "minnie35_mirrortables")])

    def test_api_exposes_expected_tables(self):
        dj = FakeDataJoint()
        api = MirrorTableAPI(
            "v1dd",
            secret_dict={"username": "user", "password": "pw"},
            datajoint_module=dj,
        )

        self.assertTrue(dj.connected)
        self.assertEqual(dj.config["database.host"], DEFAULT_HOST)
        self.assertEqual(dj.config["database.username"], "user")
        self.assertEqual(dj.config["database.user"], "user")
        self.assertEqual(dj.config["database.password"], "pw")

        self.assertIsInstance(api.auto_proofread_neuron_table, AutoProofreadNeuron)
        self.assertIsInstance(api.autoproof_obj_table, AutoProofreadNeuronObj)
        self.assertIsInstance(api.decimated_mesh_table, DecimatedMesh)
        self.assertIsInstance(api.decimated_mesh_obj_table, DecimatedMeshObj)
        self.assertIsInstance(api.decomposition_celltype_table, DecompositionCelltype)
        self.assertIsInstance(api.cell_type_obj_table, DecompositionCelltypeObj)

    def test_fetch_frame_defaults_to_pandas_frame_format(self):
        api = MirrorTableAPI("minnie35", datajoint_module=FakeDataJoint())
        result = api.fetch_frame("auto_proofread_neuron", "segment_id")
        self.assertEqual(result, {"attributes": ("segment_id",), "format": "frame"})

    def test_fetch_proofread_skeleton_uses_obj_part_table(self):
        api = MirrorTableAPI("minnie35", datajoint_module=FakeDataJoint())
        self.assertEqual(
            api.fetch_proofread_skeleton(segment_id=123, split_index=0),
            "fake-skeleton",
        )

    def test_secret_dict_accepts_user_alias(self):
        dj = FakeDataJoint()
        MirrorTableAPI(
            "minnie35",
            secret_dict={"user": "alias_user", "password": "pw"},
            datajoint_module=dj,
        )
        self.assertEqual(dj.config["database.username"], "alias_user")
        self.assertEqual(dj.config["database.user"], "alias_user")

    def test_missing_table_error_lists_available_tables(self):
        api = MirrorTableAPI("minnie35", datajoint_module=FakeDataJoint())
        with self.assertRaisesRegex(AttributeError, "Available"):
            api.table("missing_table")


if __name__ == "__main__":
    unittest.main()
