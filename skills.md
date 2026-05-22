# connects_neuvue Repository Guide

## Purpose

`connects_neuvue` is a Python package for querying CONNECTS/H01 C2 data products used by Neuvue visualizations and downstream analysis workflows. It wraps DataJoint tables, S3-backed adapted file types, and utility functions for working with neuron meshes, skeletons, NetworkX graphs, soma metadata, red/blue proofreading split suggestions, and ML training exports.

The package is primarily an access and conversion layer rather than a training or web application. Most user-facing workflows happen through the `connects_neuvue.h01_c2.API` class or through the exploratory notebooks under `Applications/`.

## Top-Level Layout

```text
.
├── README.md
├── requirements.txt
├── setup.py
├── skills.md
├── tests/
│   └── __init__.py
├── Applications/
│   ├── Datajoint_Metadata_Query/
│   └── ML_model/
└── connects_neuvue/
    ├── __init__.py
    ├── h01_c2/
    ├── mirrortables/
    └── utils/
```

## Package Structure

### `connects_neuvue.h01_c2`

This subpackage contains the H01 C2 DataJoint integration.

`api.py`

- Defines the main `API` class.
- Configures a DataJoint connection from a password or secret dictionary.
- Imports the schema tables and exposes convenient table aliases.
- Fetches neuron metadata, soma centers, soma meshes, decimated meshes, proofread meshes, compartment meshes, skeletons, NetworkX graphs, red/blue split suggestions, and ML training data.
- Provides convenience methods such as:
  - `fetch_segment_id_mesh`
  - `fetch_proofread_mesh`
  - `fetch_compartment_mesh`
  - `fetch_proofread_skeleton`
  - `nx_graph_autoproof_from_segment_id`
  - `red_blue_df`
  - `ml_training_df`

`schema.py`

- Declares DataJoint schema bindings for the `h01_process` schema.
- Creates a virtual module for existing H01 processing tables.
- Defines computed tables and part tables used by the API:
  - `MeshDecimation`
  - `SomaExtraction`
  - `DecompositionCellType`
  - `AutoProofreadNeuron`
- Uses custom adapted attribute types from `adapters.py` for file-backed objects.

`adapters.py`

- Enables DataJoint adapted types and filepath management.
- Configures S3 stores for raw meshes, decimated meshes, soma/glia/nucleus face arrays, decompositions, skeletons, graphs, and autoproof outputs.
- Reads AWS credentials through `boto3.Session()`.
- Defines adapters for:
  - Filesystem/S3-backed paths
  - NumPy arrays stored as `.npz`
  - HDF5 mesh files converted to `trimesh.Trimesh`
  - Compressed pickle files stored as `.pbz2`
- Includes `adapt_mesh_hdf5`, a helper that reads mesh vertices and faces from HDF5.

### `connects_neuvue.mirrortables`

This subpackage contains the DataJoint virtual-module integration for mirrored NEURD datasets that do not have checked-in schema files.

`api.py`

- Defines `MirrorTableAPI`, a dataset-agnostic wrapper around `dj.VirtualModule`.
- Supports the `minnie35_mirrortables` and `v1dd_mirrortables` schemas.
- Exposes the three priority mirrored tables:
  - `auto_proofread_neuron`
  - `decimated_mesh`
  - `decomposition_celltype`
- Provides convenience classes:
  - `Minnie35API`
  - `V1DDAPI`
- Provides DataFrame helpers such as `fetch_frame`, `fetch_auto_proofread_neuron_frame`, `fetch_decimated_mesh_frame`, and `fetch_decomposition_celltype_frame`.
- Configures dataset-specific S3 stores for adapted DataJoint external fields.
- Exposes H01-style aliases for part tables, including `autoproof_obj_table`, `decimated_mesh_obj_table`, and `cell_type_obj_table`.
- Fetches S3-backed proofread skeleton arrays and NetworkX graphs through helpers such as `fetch_proofread_skeleton`, `nx_graph_autoproof_from_segment_id`, `skeleton_points_from_graph_node`, and `skeleton_points_by_graph_node`.

### `connects_neuvue.utils`

Utility modules are small and focused.

`aws_utils.py`

- Checks for local AWS credentials.
- Fetches the RDS/DataJoint secret from AWS Secrets Manager.

`dj_utils.py`

- Converts a DataJoint table fetch result into a Pandas `DataFrame`.

`file_utils.py`

- Loads `.pbz2` compressed pickle files.

`neuron_utils.py`

- Stores neuron compartment groupings such as `apical_total`.

`numpy_utils.py`

- Normalizes scalar and array-like inputs.

`nx_graph_utils.py`

- Adds bounding boxes to NetworkX graph nodes that contain skeleton point data.

`skeleton_utils.py`

- Computes skeleton path distance.
- Creates empty skeleton arrays with the expected shape.

`split_suggestion_utils.py`

- Converts nested red/blue split suggestion dictionaries into records or DataFrames.
- Aggregates split suggestions by segment and error type.
- Provides plotting helpers when `datasci_tools.ipyvolume_utils` is installed.

`trimesh_utils.py`

- Provides empty mesh construction, mesh type checks, and face-index submesh extraction.

## Applications And Notebooks

`Applications/Datajoint_Metadata_Query/`

- Contains notebooks for querying H01 C2 metadata and testing API workflows.
- Includes examples for red/blue database queries, AIS queries, API tutorial usage, and skeleton point extraction from NetworkX graphs.
- Contains a `stage/` directory with example `.pbz2` graph artifacts.

`Applications/ML_model/`

- Contains notebooks for downloading ML training data from the DataJoint-backed data products.

The notebooks appear to be exploratory and workflow-oriented. The reusable code lives in the Python package.

## Runtime Dependencies

Core dependencies are listed in `requirements.txt`:

- `datajoint`
- `networkx`
- `numpy`
- `pandas`
- `bz2file`
- `trimesh`
- `boto3`
- `h5py`
- `datasci_stdlib_tools`

`setup.py` also defines a `morph_tools` extra that installs GitHub-hosted morphology/visualization tooling:

- `neuron_morphology_tools`
- `datasci_stdlib_tools`

## External Services And Credentials

This repo depends on external DataJoint and AWS infrastructure.

- The default DataJoint host in `API.__init__` is `neurd-datajoint.cluster-cjc6cqmcqirl.us-east-1.rds.amazonaws.com`.
- AWS credentials are expected through the normal local AWS credential chain, usually `~/.aws/credentials`.
- `aws_utils.get_secret()` fetches an RDS secret from AWS Secrets Manager in `us-east-1`.
- Data objects are stored in the `neurd-datalake` S3 bucket under H01-specific prefixes.

Local code inspection and pure utility testing can run without these services, but most API methods require valid DataJoint and AWS access.

## Main Data Flow

1. A user instantiates `connects_neuvue.h01_c2.API` with a database password or secret dictionary.
2. The API configures DataJoint and imports table definitions from `schema.py`.
3. DataJoint fetches table rows and adapted file paths.
4. Adapters in `adapters.py` convert file-backed values into Python objects such as NumPy arrays, `trimesh.Trimesh` meshes, compressed pickle objects, or paths.
5. API methods combine these objects into higher-level outputs such as compartment meshes, soma meshes, skeletons, split suggestion DataFrames, and ML training DataFrames.

## Development Notes

- The test suite is currently only a package placeholder in `tests/__init__.py`; there are no substantive tests yet.
- The README still contains a generic project tree template, so this file should be treated as the more accurate repository map.
- Some optional visualization imports are best-effort and warn when unavailable.
- Several methods assume live external data access, so unit tests should prefer pure utility functions or mocked DataJoint/S3 interactions.
- The `.ipynb_checkpoints` files are notebook/editor artifacts and should not be treated as source-of-truth code.
