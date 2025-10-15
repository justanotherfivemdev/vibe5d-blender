# Query Module

This module provides SQL-like querying capabilities for Blender scene data with LLM-optimized output formats.

## Architecture

The query system uses denormalized, document-like data structures with streaming iterators for efficient performance on
large scenes.

### Core Components

- **`engine.py`** - Main `SceneQueryEngine` orchestrator with table registry
- **`parser.py`** - `QueryParser` for SQL-like query parsing
- **`response.py`** - `QueryResponse` for standardized query responses
- **`conditions.py`** - `WhereCondition` and `WhereExpression` for filtering
- **`aggregates.py`** - `AggregateFunction` for SQL aggregate operations
- **`formatters.py`** - Output formatters (Compact, Columnar, Graph)
- **`base_table.py`** - Base class for all table implementations

### Table Classes (`tables/`)

Each table is implemented as a separate class with streaming iterators:

- **`objects.py`** - Scene objects with embedded modifiers, constraints, type-specific data
- **`materials.py`** - Materials with complete node trees
- **`lights.py`** - Light data
- **`cameras.py`** - Camera data
- **`collections.py`** - Collection hierarchy
- **`scene.py`** - Scene configuration with render settings
- **`world.py`** - World environment with node trees
- **`meshes.py`** - Mesh geometry data blocks
- **`images.py`** - Image data blocks
- **`modifiers.py`** - Standalone modifier queries
- **`constraints.py`** - Standalone constraint queries
- **`custom_properties.py`** - Custom properties
- **`texts.py`** - Text data blocks
- **`curves.py`** - Curve data blocks
- **`tables.py`** - Meta-table listing all tables

## Available Tables

| Table               | Description                                                              |
|---------------------|--------------------------------------------------------------------------|
| `objects`           | Scene objects with transform, modifiers, constraints, type-specific data |
| `materials`         | Material data with embedded node graphs                                  |
| `lights`            | Light objects and properties                                             |
| `cameras`           | Camera objects and settings                                              |
| `collections`       | Collection hierarchy and contents                                        |
| `scene`             | Current scene configuration including render settings                    |
| `world`             | World shader and environment with node tree                              |
| `meshes`            | Mesh geometry data blocks                                                |
| `images`            | Image data blocks                                                        |
| `modifiers`         | Object modifiers (queryable separately)                                  |
| `constraints`       | Object constraints (queryable separately)                                |
| `custom_properties` | Custom properties from data blocks                                       |
| `texts`             | Text data blocks                                                         |
| `curves`            | Curve data blocks                                                        |
| `tables`            | Meta-table listing all available tables                                  |

## Output Formats

The system uses smart auto-format selection based on data characteristics:

### Compact Format

**Use:** Heterogeneous data (different schemas per row)
**Example:**

```
name=Cube type=MESH loc=[0,0,0] vis=1 mats=[Metal]
name=Light type=LIGHT loc=[5,5,5] energy=1000 color=[1,1,1]
```

### Columnar Format

**Use:** Homogeneous data (same schema across rows)
**Example:**

```
name      type  location
Cube      MESH  [0,0,0]
Sphere    MESH  [2,3,1]
```

### Graph Format

**Use:** Node trees in materials/world
**Example:**

```
GRAPH Material.Gold
N1=PrincipledBSDF metal=1.0 rough=0.2
N2=ImageTexture img=gold.png
N2:Color->N1:BaseColor
```

## Query Examples

### Basic Queries

```sql
-- Get all mesh objects
SELECT name, type, location FROM objects WHERE type='MESH'

-- Get visible objects
SELECT name, visible, location FROM objects WHERE visible=1

-- Get materials with node trees
SELECT name, use_nodes FROM materials WHERE use_nodes=1

-- Get scene configuration
SELECT * FROM scene
```

### With Node Graphs

```sql
-- Get material with embedded node graph
SELECT name, node_graph FROM materials WHERE name='Gold'
```

### Aggregates

```sql
-- Count objects by type
SELECT COUNT(*) FROM objects WHERE type='MESH'

-- Average light energy
SELECT AVG(energy) FROM lights
```

### Embedded Data

```sql
-- Get objects with modifiers
SELECT name, type, modifiers FROM objects WHERE type='MESH'

-- Get materials with complete node trees
SELECT * FROM materials
```

## Performance

- **Streaming iterators**: Only loads requested data
- **Field selection**: Skips expensive nested data unless explicitly requested
- **WHERE push-down**: Filters during iteration, not after
- **Early termination**: Stops at LIMIT
- **Token-efficient formats**: 50-80% reduction vs JSON

## Design Principles

1. **Denormalized data**: Complete context in one query
2. **Streaming**: Efficient for large scenes
3. **Token optimization**: Minimal output for LLM consumption
4. **Smart formatting**: Auto-select best format for data structure
