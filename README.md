# connects_neuvue
a package with API defined for querying connects data products for neuvue visualizations and other downstream tasks

## Mirror Table Datasets

The `minnie35` and `v1dd` NEURD mirror databases do not require checked-in schema files. They can be reflected at runtime with DataJoint virtual modules:

```python
from connects_neuvue import Minnie35API, V1DDAPI

api = Minnie35API(secret_dict={"username": "admin", "password": "..."})

auto_df = api.fetch_auto_proofread_neuron_frame(limit=10)
mesh_table = api.decimated_mesh_table
celltype_table = api.decomposition_celltype_table
```

The generic API also accepts an explicit dataset name:

```python
from connects_neuvue import MirrorTableAPI

api = MirrorTableAPI("v1dd", secret_dict={"username": "admin", "password": "..."})
df = api.fetch_frame("auto_proofread_neuron", limit=10)
```

Part-table payloads are available through H01-style aliases and helper methods:

```python
api = MirrorTableAPI(
    "minnie35",
    secret_dict={"username": "admin", "password": "..."},
    aws_profile="proof",
)
key = api.autoproof_obj_table.fetch("KEY", limit=1)[0]

proofread_skeleton = api.fetch_proofread_skeleton(**key)
graph = api.nx_graph_autoproof_from_segment_id(**key)
skeleton_points = api.skeleton_points_by_graph_node(**key)
```

Supported reflected schemas:

- `minnie35` -> `minnie35_mirrortables`
- `v1dd` -> `v1dd_mirrortables`

Supported reflected tables:

- `auto_proofread_neuron`
- `decimated_mesh`
- `decomposition_celltype`

## 📦 Installation

### 🔹 Basic Installation

To install the package and its core dependencies, run:

```bash
pip install .
```

### 🔹 With Optional Dependencies

To include optional tools like `neuron_morphology_tools` from GitHub, use:

```bash
pip install .[morph_tools]
```

> 💡 `morph_tools` corresponds to the optional extras defined in `setup.py`. This package will help with any visualizations of the neuron networkx objects

### 🔹 Development Mode

If you're actively developing the package and want changes to reflect immediately:

```bash
pip install -e .
```

To include the optional extras in development mode:

```bash
pip install -e .[morph_tools]
```

### 🔹 Install Directly from GitHub (Optional)

If the project is hosted on GitHub, you can install it directly with:

```bash
pip install git+https://github.com/yourusername/your_project.git
```

## 📁 Project Structure

```
your_project/
├── your_project/           # Main package
│   ├── __init__.py
│   └── ...                 # Your modules
├── tests/                  # Unit tests
│   └── __init__.py
├── setup.py                # Installation script
├── requirements.txt        # Core dependencies
├── README.md               # Project overview
├── LICENSE                 # Optional
└── .gitignore              # Git ignore rules
```
