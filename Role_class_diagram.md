# Class Diagram - Registration Deadline

```mermaid
classDiagram
    class Conference {
        +int conference_id
        +str name
        +str description
        +datetime event_datetime
        +str location
        +str registration_type
        +int capacity
        +date registration_deadline
        +bool is_published
        +datetime published_at
        +is_registration_open() bool
        +validate_conference_form(form) tuple
    }
    class Participant {
        +int participant_id
        +str name
        +str email
    }
    class Registration {
        +int registration_id
        +int conference_id
        +int participant_id
        +datetime registered_at
    }
    Conference "1" -- "0..*" Registration : has
    Participant "1" -- "0..*" Registration : makes
