# 3. Decentralized Dependency Injection with a Composition Root

**Date**: 2024-08-01

**Status**: Accepted

## Context

As the application grew, the initial dependency injection strategy relied on a single, centralized `ApplicationContainer` located in the `shared` module. This container was responsible for constructing and providing every service, repository, and handler for all modules.

This approach presented several architectural problems:

-   **High Coupling**: The `shared` module became a central point of coupling, as it needed to import components from every other module in the application to construct them. This violated the principle of isolated Bounded Contexts.
-   **Difficult Maintenance**: Any change to a service's constructor required a change in this central container, increasing the risk of merge conflicts and making refactoring cumbersome.
-   **Poor Scalability to Microservices**: If we ever decided to extract a module (e.g., `auth`) into a separate microservice, untangling its construction logic from the central container would be a complex and error-prone task.

## Decision

We decided to completely decentralize dependency injection by adopting a **Composition Root** pattern at the application's entry point (`main.py`).

1.  **Per-Module Bootstrapping**: Each business module (e.g., `auth`, `media_management`) now has its own `bootstrap.py` file. This file contains a `bootstrap_*_module` function responsible for constructing all the services, handlers, and queries specific to that module.

2.  **Explicit Composition Root**: The `main.py` file now acts as the single, explicit "Composition Root". Inside the `lifespan` context manager, it performs the following steps:
    -   Initializes truly shared, cross-cutting concerns (like the `EventBus` and service factories).
    -   Calls the `bootstrap` function for each module.
    -   Explicitly injects any cross-context dependencies (e.g., passing the `UserRepository` from the `auth` module into the `notifications` module).
    -   Composes the final application-wide container as a simple dictionary, which is then attached to the application state.

3.  **Removal of Central Container**: The old `ApplicationContainer` class was completely removed.

## Consequences

### Positive

-   **True Decoupling**: Modules are now truly self-contained in their construction. The `auth` module, for example, has no knowledge of the `video_processing` module, and vice-versa.
-   **Explicit Dependencies**: Cross-context dependencies are now explicit and visible in one place (`main.py`), making the overall system architecture much easier to understand and reason about.
-   **Improved Maintainability**: Adding or changing a service's dependencies only requires changes within that service's own module.
-   **Ready for Microservices**: Extracting a module into a separate service is now significantly easier, as all of its construction logic is already isolated.

### Negative

-   **More Boilerplate for Bootstrapping**: Each module now requires its own `bootstrap.py` file.
-   **Composition Logic in `main.py`**: The composition logic in `main.py` is more complex than before, as it manually wires together the different modules. However, this complexity is contained in a single, appropriate location.

This trade-off was deemed highly beneficial, as it enforces a clean, decoupled architecture that is critical for the long-term health and scalability of the project.
