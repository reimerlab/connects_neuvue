"""
Adapted DataJoint types and S3 store configuration for mirror-table datasets.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import h5py
import numpy as np
import trimesh

from ..utils import file_utils as fileu


os.environ["DJ_SUPPORT_ADAPTED_TYPES"] = "TRUE"
os.environ["DJ_SUPPORT_FILEPATH_MANAGEMENT"] = "TRUE"

BUCKET = "neurd-datalake"
STAGE = os.path.abspath("./stage")

DATASET_S3_PREFIXES = {
    "minnie35": "minnie35",
    "v1dd": "v1deepdive",
}

DATASET_STORE_LOCATIONS = {
    "minnie35": {
        "auto_proof_decomposition": "minnie35/auto_proof_decompositions",
        "auto_proof_graph": "minnie35/auto_proof_graph",
        "auto_proof_meshes": "minnie35/auto_proof_meshes",
        "auto_proof_skeletons": "minnie35/auto_proof_skeletons",
        "decimated_meshes": "minnie35/decimated_meshes",
        "decompositions": "minnie35/decompositions",
        "graph": "minnie35/graph",
        "skeletons": "minnie35/skeletons",
    },
    "v1dd": {
        "auto_proof_decomposition": "v1deepdive/auto_proof_decompositions",
        "auto_proof_graph": "v1deepdive/auto_proof_graph",
        "auto_proof_meshes": "v1deepdive/auto_proof_meshes",
        "auto_proof_skeletons": "v1deepdive/auto_proof_skeletons",
        "decimated_meshes": "v1deepdive/decimated_meshes",
        "decomposition": "v1deepdive/decompositions",
        "decompositions": "v1deepdive/decompositions",
        "graph": "v1deepdive/graph",
    },
}


def validate_filepath(filepath):
    filepath = Path(filepath)
    if not filepath.exists():
        raise FileNotFoundError(filepath)
    return filepath


def adapt_mesh_hdf5(filepath, parse_filepath_stem=True):
    from collections import namedtuple

    Mesh = namedtuple("Mesh", ["vertices", "faces", "segment_id", "filepath"])
    filepath = Path(filepath)
    segment_id = np.nan
    if parse_filepath_stem:
        try:
            segment_id = int(filepath.stem)
        except ValueError:
            pass

    with h5py.File(filepath, "r") as f:
        vertices = f["vertices"][()].astype(np.float64)
        faces = f["faces"][()].reshape(-1, 3).astype(np.uint32)

    return Mesh(
        vertices=vertices,
        faces=faces,
        segment_id=segment_id,
        filepath=filepath,
    )


def _aws_credentials(aws_profile: str | None = None):
    import boto3

    session = boto3.Session(profile_name=aws_profile) if aws_profile else boto3.Session()
    credentials = session.get_credentials()
    if credentials is None:
        return None
    return credentials.get_frozen_credentials()


def _s3_store(location: str, credentials: Any | None):
    store = {
        "secure": True,
        "stage": STAGE,
        "protocol": "s3",
        "endpoint": "s3.amazonaws.com",
        "bucket": BUCKET,
        "location": location,
    }
    if credentials is not None:
        store["access_key"] = credentials.access_key
        store["secret_key"] = credentials.secret_key
        if credentials.token is not None:
            store["session_token"] = credentials.token
    return store


def configure_dataset_stores(dj, dataset: str, *, aws_profile: str | None = None):
    try:
        locations = DATASET_STORE_LOCATIONS[dataset]
    except KeyError as exc:
        valid = ", ".join(sorted(DATASET_STORE_LOCATIONS))
        raise ValueError(f"Unknown mirror-table dataset {dataset!r}. Expected one of: {valid}") from exc

    credentials = _aws_credentials(aws_profile=aws_profile)
    stores = dict(dj.config.get("stores", {}))
    for store_name, location in locations.items():
        stores[store_name] = _s3_store(location, credentials)
    dj.config["stores"] = stores
    return stores


def create_adapted_type_objects(dj):
    class Adapter(dj.AttributeAdapter):
        attribute_type = ""

        def __init__(self, attribute_type: str):
            self.attribute_type = attribute_type
            super().__init__()

    class FilePathAdapter(Adapter):
        def put(self, filepath):
            return validate_filepath(filepath)

        def get(self, filepath):
            return validate_filepath(filepath)

    class NumpyAdapter(FilePathAdapter):
        def get(self, filepath):
            filepath = super().get(filepath)
            return np.load(filepath, mmap_mode="r", allow_pickle=True)["arr_0"]

    class TrimeshAdapter(FilePathAdapter):
        def get(self, filepath):
            filepath = super().get(filepath)
            if filepath.suffix == ".h5":
                mesh = adapt_mesh_hdf5(filepath, parse_filepath_stem=False)
                return trimesh.Trimesh(vertices=mesh.vertices, faces=mesh.faces)
            return filepath

    class PbzPickleAdapter(FilePathAdapter):
        def get(self, filepath):
            filepath = super().get(filepath)
            return fileu.decompress_pickle(filepath)

    return {
        "decimated_mesh": TrimeshAdapter("filepath@decimated_meshes"),
        "decompositions": FilePathAdapter("filepath@decompositions"),
        "decomposition": FilePathAdapter("filepath@decomposition"),
        "skeletons": PbzPickleAdapter("filepath@skeletons"),
        "graph": FilePathAdapter("filepath@graph"),
        "auto_proof_meshes_dtype": PbzPickleAdapter("filepath@auto_proof_meshes"),
        "auto_proof_skeletons_dtype": PbzPickleAdapter("filepath@auto_proof_skeletons"),
        "auto_proof_graph_dtype": FilePathAdapter("filepath@auto_proof_graph"),
        "auto_proof_decomposition_dtype": FilePathAdapter("filepath@auto_proof_decomposition"),
    }
