"""
DataJoint virtual-module access for mirrored NEURD datasets.

The minnie35 and v1dd mirror databases expose tables that match the NEURD
database contents, but this repository does not carry handwritten schema
classes for them. DataJoint virtual modules can reflect those schemas at
runtime, so this module provides a thin wrapper around ``dj.VirtualModule``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from ..utils import file_utils as fileu
from ..utils import nx_graph_utils as nxgu
from .adapters import configure_dataset_stores, create_adapted_type_objects


DEFAULT_HOST = "neurd-datajoint.cluster-cjc6cqmcqirl.us-east-1.rds.amazonaws.com"

DATASET_SCHEMAS = {
    "minnie35": "minnie35_mirrortables",
    "v1dd": "v1dd_mirrortables",
}

MIRROR_TABLES = {
    "auto_proofread_neuron": ("AutoProofreadNeuron",),
    "decimated_mesh": ("DecimatedMesh",),
    "decomposition_celltype": (
        "DecompositionCelltype",
        "DecompositionCellType",
    ),
}


def _import_datajoint():
    try:
        import datajoint as dj
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError(
            "DataJoint is required to use connects_neuvue.mirrortables. "
            "Install this package's requirements before opening a live "
            "mirror-table connection."
        ) from exc
    return dj


def secret_dict_from_password(password: str | None, username: str = "admin") -> dict[str, str | None]:
    return {"username": username, "password": password}


def schema_name_from_dataset(dataset: str) -> str:
    try:
        return DATASET_SCHEMAS[dataset]
    except KeyError as exc:
        valid = ", ".join(sorted(DATASET_SCHEMAS))
        raise ValueError(f"Unknown dataset {dataset!r}. Expected one of: {valid}") from exc


def create_virtual_module(
    dataset: str,
    *,
    module_name: str | None = None,
    schema_name: str | None = None,
    configure_stores: bool = True,
    aws_profile: str | None = None,
    datajoint_module: Any | None = None,
):
    """
    Create a DataJoint virtual module for a mirror-table dataset.
    """
    dj = datajoint_module or _import_datajoint()
    schema_name = schema_name or schema_name_from_dataset(dataset)
    module_name = module_name or dataset
    add_objects = None

    if configure_stores and hasattr(dj, "AttributeAdapter"):
        configure_dataset_stores(dj, dataset, aws_profile=aws_profile)
        add_objects = create_adapted_type_objects(dj)

    if hasattr(dj, "VirtualModule"):
        return dj.VirtualModule(
            module_name=module_name,
            schema_name=schema_name,
            add_objects=add_objects,
        )
    return dj.create_virtual_module(module_name, schema_name, add_objects=add_objects)


def _maybe_instantiate(table: Any):
    try:
        return table()
    except TypeError:
        return table


@dataclass(frozen=True)
class MirrorDataset:
    dataset: str
    schema_name: str
    module_name: str


class MirrorTableAPI:
    """
    Convenience API for reflected NEURD mirror tables.

    Parameters
    ----------
    dataset:
        Dataset key. Currently ``"minnie35"`` or ``"v1dd"``.
    secret_password, secret_dict, host:
        Optional DataJoint connection settings. If omitted, the caller's
        existing DataJoint configuration is used.
    connect:
        When true, call ``dj.conn()`` after applying connection settings.
    datajoint_module:
        Test hook for injecting a fake DataJoint module.
    """

    table_attrs = MIRROR_TABLES

    def __init__(
        self,
        dataset: str,
        *,
        secret_password: str | None = None,
        secret_dict: Mapping[str, str | None] | None = None,
        username: str = "admin",
        host: str | None = DEFAULT_HOST,
        module_name: str | None = None,
        schema_name: str | None = None,
        connect: bool = True,
        configure_stores: bool = True,
        aws_profile: str | None = None,
        datajoint_module: Any | None = None,
    ):
        self.dj = datajoint_module or _import_datajoint()
        self.dataset = dataset
        self.schema_name = schema_name or schema_name_from_dataset(dataset)
        self.module_name = module_name or dataset

        if secret_dict is None and secret_password is not None:
            secret_dict = secret_dict_from_password(secret_password, username=username)

        self._configure_connection(host=host, secret_dict=secret_dict)
        if connect:
            self.dj.conn()

        self.module = create_virtual_module(
            dataset,
            module_name=self.module_name,
            schema_name=self.schema_name,
            configure_stores=configure_stores,
            aws_profile=aws_profile,
            datajoint_module=self.dj,
        )
        self.info = MirrorDataset(
            dataset=self.dataset,
            schema_name=self.schema_name,
            module_name=self.module_name,
        )

        self.auto_proofread_neuron_table = self.table("auto_proofread_neuron")
        self.autoproof_table = self.auto_proofread_neuron_table
        self.proofreading_neurons_table_raw = self.autoproof_table
        self.autoproof_obj_table = self.part_table("auto_proofread_neuron", "Obj")
        self.proofreading_object_table = self.autoproof_obj_table
        self.autoproof_error_stats_table = self.part_table("auto_proofread_neuron", "ErrorStats")
        self.autoproof_synapse_table = self.part_table("auto_proofread_neuron", "Synapse")
        self.autoproof_synapse_errors_table = self.part_table("auto_proofread_neuron", "SynapseErrors")

        self.decimated_mesh_table = self.table("decimated_mesh")
        self.decimated_mesh_obj_table = self.part_table("decimated_mesh", "Obj")

        self.decomposition_celltype_table = self.table("decomposition_celltype")
        self.cell_type_table = self.decomposition_celltype_table
        self.cell_type_obj_table = self.part_table("decomposition_celltype", "Obj")

    def _configure_connection(
        self,
        *,
        host: str | None,
        secret_dict: Mapping[str, str | None] | None,
    ) -> None:
        if host is not None:
            self.dj.config["database.host"] = host

        if secret_dict is None:
            return

        username = secret_dict.get("username", secret_dict.get("user"))
        password = secret_dict.get("password")
        if username is not None:
            self.dj.config["database.username"] = username
            self.dj.config["database.user"] = username
        if password is not None:
            self.dj.config["database.password"] = password

    @property
    def available_table_attrs(self) -> list[str]:
        return [
            name
            for name in dir(self.module)
            if name[:1].isupper() and not name.startswith("_")
        ]

    def table(self, table_name: str):
        """
        Return a reflected DataJoint table relation.

        ``table_name`` may be a canonical snake-case name such as
        ``"auto_proofread_neuron"`` or a virtual-module attribute name such as
        ``"AutoProofreadNeuron"``.
        """
        attr_candidates = self.table_attrs.get(table_name, (table_name,))

        for attr in attr_candidates:
            if hasattr(self.module, attr):
                return _maybe_instantiate(getattr(self.module, attr))

        available = ", ".join(self.available_table_attrs) or "<none>"
        expected = ", ".join(attr_candidates)
        raise AttributeError(
            f"Could not find table {table_name!r} on virtual module "
            f"{self.module_name!r}. Tried: {expected}. Available: {available}"
        )

    def part_table(self, table_name: str, part_name: str):
        parent = self.table(table_name)
        parent_cls = parent.__class__
        if hasattr(parent_cls, part_name):
            return _maybe_instantiate(getattr(parent_cls, part_name))
        raise AttributeError(f"Could not find part table {table_name}.{part_name}")

    @staticmethod
    def _primary_key_names(table) -> list[str]:
        heading = getattr(table, "heading", None)
        if heading is not None and hasattr(heading, "primary_key"):
            return list(heading.primary_key)
        if hasattr(table, "primary_key"):
            return list(table.primary_key)
        return []

    def segment_key(
        self,
        segment_id: int,
        *,
        split_index: int = 0,
        decimation_ratio: Any | None = None,
        table=None,
    ) -> dict[str, Any]:
        table = table or self.autoproof_obj_table
        primary_key = self._primary_key_names(table)
        key = {"segment_id": segment_id}
        if "split_index" in primary_key:
            key["split_index"] = split_index
        if "decimation_ratio" in primary_key and decimation_ratio is not None:
            key["decimation_ratio"] = decimation_ratio
        return key

    def fetch_compartment_skeleton(
        self,
        compartment: str,
        segment_id: int,
        *,
        split_index: int = 0,
        decimation_ratio: Any | None = None,
    ):
        field = f"{compartment}_skeleton"
        key = self.segment_key(
            segment_id,
            split_index=split_index,
            decimation_ratio=decimation_ratio,
            table=self.autoproof_obj_table,
        )
        return (self.autoproof_obj_table & key).fetch1(field)

    def fetch_proofread_skeleton(
        self,
        segment_id: int,
        *,
        split_index: int = 0,
        decimation_ratio: Any | None = None,
    ):
        return self.fetch_compartment_skeleton(
            "neuron",
            segment_id,
            split_index=split_index,
            decimation_ratio=decimation_ratio,
        )

    def fetch_proofread_skeleton_axon(self, segment_id: int, **kwargs):
        return self.fetch_compartment_skeleton("axon", segment_id, **kwargs)

    def fetch_proofread_skeleton_dendrite(self, segment_id: int, **kwargs):
        return self.fetch_compartment_skeleton("dendrite", segment_id, **kwargs)

    def fetch_neuron_graph_path(
        self,
        segment_id: int,
        *,
        split_index: int = 0,
        decimation_ratio: Any | None = None,
    ):
        key = self.segment_key(
            segment_id,
            split_index=split_index,
            decimation_ratio=decimation_ratio,
            table=self.autoproof_obj_table,
        )
        return (self.autoproof_obj_table & key).fetch1("neuron_graph")

    def nx_graph_autoproof_from_segment_id(
        self,
        segment_id: int,
        *,
        split_index: int = 0,
        decimation_ratio: Any | None = None,
        add_bounding_box: bool = True,
    ):
        graph_path = self.fetch_neuron_graph_path(
            segment_id,
            split_index=split_index,
            decimation_ratio=decimation_ratio,
        )
        graph = fileu.decompress_pickle(graph_path)
        if add_bounding_box:
            nxgu.add_bounding_boxes_to_graph(graph)
        return graph

    def skeleton_points_from_graph_node(
        self,
        segment_id: int,
        node_name: str,
        *,
        split_index: int = 0,
        decimation_ratio: Any | None = None,
    ):
        graph = self.nx_graph_autoproof_from_segment_id(
            segment_id,
            split_index=split_index,
            decimation_ratio=decimation_ratio,
        )
        skeleton_data = graph.nodes[node_name].get("skeleton_data")
        if skeleton_data is None:
            raise KeyError(f"Graph node {node_name!r} does not contain skeleton_data")
        return skeleton_data

    def skeleton_points_by_graph_node(
        self,
        segment_id: int,
        *,
        split_index: int = 0,
        decimation_ratio: Any | None = None,
    ) -> dict[str, Any]:
        graph = self.nx_graph_autoproof_from_segment_id(
            segment_id,
            split_index=split_index,
            decimation_ratio=decimation_ratio,
        )
        return {
            node: data["skeleton_data"]
            for node, data in graph.nodes(data=True)
            if data.get("skeleton_data") is not None
        }

    def fetch_frame(self, table_name: str, *attributes: str, **kwargs):
        """
        Fetch a mirror table as a Pandas DataFrame.
        """
        kwargs.setdefault("format", "frame")
        return self.table(table_name).fetch(*attributes, **kwargs)

    def fetch_auto_proofread_neuron_frame(self, *attributes: str, **kwargs):
        return self.fetch_frame("auto_proofread_neuron", *attributes, **kwargs)

    def fetch_decimated_mesh_frame(self, *attributes: str, **kwargs):
        return self.fetch_frame("decimated_mesh", *attributes, **kwargs)

    def fetch_decomposition_celltype_frame(self, *attributes: str, **kwargs):
        return self.fetch_frame("decomposition_celltype", *attributes, **kwargs)


class Minnie35API(MirrorTableAPI):
    def __init__(self, **kwargs):
        super().__init__("minnie35", **kwargs)


class V1DDAPI(MirrorTableAPI):
    def __init__(self, **kwargs):
        super().__init__("v1dd", **kwargs)
