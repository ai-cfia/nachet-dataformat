# Datastore

Welcome to the Datastore - the integral data management layer of the Nachet and
FertiScan solution serving a dual function role. As a central repository, it
efficiently manages multimedia storage in the blob storage server while
concurrently ensuring accurate metadata registration into a database server.

## Robust Multimedia Storage

The essential function of our Datastore is to manage the multimedia storage
effectively within the blob storage server. With support for a variety of media
formats and efficient indexing techniques, the smooth retrieval and access of
data are assured.

```Structure

Storage account:
│     
│  Container:
└───user-8367cc4e-1b61-42c2-a061-ca8662aeac37
|   | Folder:
│   └───folder-name/
|   |  |   fb20146f-df2f-403f-a56f-f02a48092167.json
│   |  │   f9b0ef75-6276-4ffc-a71c-975bc842063c.tiff
│   |  │   68e16a78-24bd-4b8c-91b6-75e6b84c40d8.tiff
│   |  |   ...
│   |  └─────────────
|   | Folder:
│   └───other-folder-name/
│      |   ...
│      └─────────────
|   Container:
└───user-...
|   └── ...
└──────────────────

```

## Efficient Metadata Registration

Coupled with managing multimedia storage, the Datastore also seamlessly
registers metadata into a database server. This double-edged approach ensures
not just efficient storage, but also the organization and easy accessibility of
your valuable data.

``` mermaid

---
title: Project Layers
---
flowchart LR;
    FE(Frontend)
    BE(Backend)
    file[/Client/]
    classDef foo stroke:#f00

    file ==> FE
    FE-->BE
    MD(Datastore)
    DB[(Database)] 
    blob[(Blob Storage)]
    ML[(AI Models)]
    BE --> MD
    BE -- pipeline --->ML
    MD --> DB
    MD --> blob
```

### Datastore module

The Datastore module assures the CRUD workflow of the following high level entitites.

```mermaid
---
title: Project Layers
---
classDiagram


    class Folder {
        UUID id
        str name
        str path
        List~UUID~ children
        List~UUID~ pictures
        Optional~UUID~ parent_id
    }

    class Container {
        UUID id
        str name
        bool is_public
        str storage_prefix
        List~UUID~ group_ids
        List~UUID~ user_ids
        Dict~UUID, Folder~ folders
        str path
    }

    class ContainerController {
        UUID id
        Optional~Container~ model
        Optional~ContainerClient~ container_client
        +__init__(self, id: UUID)
        +fetch_all_folders_metadata(self, cursor: Cursor)
        +__build_children_path(self, folder_id: UUID)
        +fetch_all_data(self, cursor: Cursor)
        +__remove_folder_and_children(self, folder_id: UUID)
        +get_container_client(self, connection_str: str, credentials: str)
        +get_id(self)
        +add_user(self, cursor: Cursor, user_id: UUID, performed_by: UUID)
        +remove_user(self, cursor: Cursor, user_id: UUID)
        +add_group(self, cursor: Cursor, group_id: UUID, performed_by: UUID)
        +remove_group(self, cursor: Cursor, group_id: UUID)
        +create_storage(self, connection_str: str, credentials: str)
        +create_folder(self, cursor: Cursor, performed_by: UUID, folder_name: str, nb_pictures: int, parent_folder_id: UUID)
        +upload_pictures(self, cursor: Cursor, user_id: UUID, hashed_pictures: List~str~, folder_id: UUID, nb_objects: int)
        +get_folder_pictures(self, cursor: Cursor, folder_id: UUID, user_id: UUID)
        +get_picture_blob(self, cursor: Cursor, picture_id: UUID, user_id: UUID)
        +delete_folder_permanently(self, cursor: Cursor, user_id: UUID, folder_id: UUID)
        +delete_picture_permanently(self, cursor: Cursor, user_id: UUID, picture_id: UUID)
    }

    class Client {
        UUID id
        str name
        bool is_public
        str storage_prefix
        Dict~UUID, Container~ containers
    }

    class ClientController {
        UUID id
        Client model
        +__init__(self, client_model: Client)
        +get_name(self)
        +get_id(self)
        +get_containers(self)
        +create_container(self, cursor: Cursor, connection_str: str, name: str, user_id: UUID, is_public: bool) ContainerController
        +fetch_all_containers(self, cursor: Cursor)
    }

    class User {
        +__init__(self, email: str, id: UUID, tier: str)
        +fetch_all_containers(self, cursor: Cursor, connection_str: str, credentials: str)
    }

    class Group {
        +__init__(self, name: str, id: UUID)
        +create_container(self, cursor: Cursor, connection_str: str, name: str, user_id: UUID, is_public: bool) ContainerController
        +fetch_all_containers(self, cursor: Cursor)
        +add_user(self, cursor: Cursor, user_id: UUID, performed_by: UUID)
        +remove_user(self, cursor: Cursor, user_id: UUID)
    }

    Folder <.. ContainerController : model
    Container <.. ContainerController: model
    Client <.. ClientController: model
    ClientController<|-- User
    ClientController<|--Group
```

## Database Architecture

```mermaid
---
title: Current Schema
---
erDiagram
    USERS {
        UUID id PK
        TEXT email
        TIMESTAMP registration_date
        TIMESTAMP updated_at
    }

    GROUPS {
        UUID id PK
        TEXT name
        TIMESTAMP created_at
        TIMESTAMP updated_at
        UUID created_by_id FK
    }

    USER_GROUP {
        UUID id PK
        UUID user_id FK
        UUID group_id FK
        TIMESTAMP updated_at
        UUID assigned_by_id FK
    }

    CONTAINER {
        UUID id PK
        TEXT name
        BOOLEAN is_public
        TEXT storage_prefix
        TIMESTAMP created_at
        TIMESTAMP updated_at
        UUID created_by_id FK
        UUID last_updated_by_id FK
    }

    CONTAINER_USER {
        UUID id PK
        UUID user_id FK
        TIMESTAMP created_at
        TIMESTAMP updated_at
        UUID created_by_id FK
        UUID last_updated_by_id FK
        UUID container_id FK
    }

    CONTAINER_GROUP {
        UUID id PK
        UUID group_id FK
        TIMESTAMP created_at
        TIMESTAMP updated_at
        UUID created_by_id FK
        UUID last_updated_by_id FK
        UUID container_id FK
    }

    USERS ||--o{ GROUPS : "creates"
    USERS ||--o{ USER_GROUP : "group access"
    GROUPS ||--o{ USER_GROUP : "members"
    USERS ||--o{ CONTAINER : "creates"
    USERS ||--o{ CONTAINER_USER : "individual access"
    CONTAINER ||--o{ CONTAINER_USER : "access to"
    GROUPS ||--o{ CONTAINER_GROUP : "access to"
```

  For more detail on each app database architecture go check [Nachet
  Architecture](../../nachet/doc/nachet-architecture.md) and [Fertiscan
  Architecture](../../fertiscan/doc/fertiScan-architecture.md).

### Global Needs

- A User must be able to take a picture on the app, it must be saved in the
  blob Storage and also tracked into the DB.

- A User can upload a batch on pictures.

- A User can verify the result of a picture that went through the pipeline and
  the changes are saved for training.

- A User can create a group of User

- A User can manage who (User & Group) has access to their containers
