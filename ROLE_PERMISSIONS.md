# Role Permissions

The application supports three mutually exclusive roles: **Admin**, **Organizer**, and **Participant**.

| Capability                               | Admin                                                  | Organizer                                                | Participant                                                                           |
|------------------------------------------|--------------------------------------------------------|----------------------------------------------------------|---------------------------------------------------------------------------------------|
| Create users                             | All users                                              | No                                                       | No                                                                                    |
| View another user's profile              | Yes                                                    | No                                                       | No                                                                                    |
| Delete users                             | Yes                                                    | No                                                       | No                                                                                    |
| View published conferences               | All published open conferences                         | All published open conferences                           | All published open conferences and restricted conferences for which access is granted |
| Create conferences                       | Yes                                                    | Yes                                                      | No                                                                                    |
| View unpublished conferences             | Any conference                                         | Only conferences they own                                | No                                                                                    |
| Publish conferences                      | Any conference                                         | Only conferences they own                                | No                                                                                    |
| Manage conference details                | Any conference                                         | Only conferences they own                                | No                                                                                    |
| Invite participants                      | Any restricted conference                              | Only restricted conferences they own                     | No                                                                                    |
| Remove or update conference participants | Any conference                                         | Only conferences they own                                | No                                                                                    |
| Export participant data                  | Any conference                                         | Only conferences they own                                | No                                                                                    |
| View conference audit logs               | All conferences                                        | Only conferences they own                                | No                                                                                    |
| Register for conferences                 | Any conference, including restricted conferences       | Permitted conferences other than their own               | Permitted conferences                                                                 |
| Cancel a registration                    | Any user's registration                                | Only their own registration when acting as a participant | Only their own registration                                                           |
| Download registration receipts           | Any registration associated with the signed-in account | Only their own registration when acting as a participant | Only their own registration                                                           |
| View upcoming attendance                 | All upcoming registrations                             | Only their own attendance when also a participant        | Only their own attendance                                                             |
| View past attendance                     | No special access through the participant-only page    | No, unless also a participant                            | Their own past attendance                                                             |

## Ownership rules

- Admins have system-wide conference management access.
- Organizers may manage only conferences where their user ID is the conference owner.
- Participants may manage only their own registrations and attendance data.
- A user must have exactly one role.

## Backend enforcement

Authorization is enforced by the Flask routes and the database-backed service functions. The interface hides unavailable actions, but backend checks remain authoritative.

- Unauthenticated requests receive `401 Login required`.
- Authenticated users without permission receive `403 Forbidden`.
- Requests for a conference that does not exist receive `404 Conference not found`.
- Requests for an existing conference that the authenticated user cannot access receive `403 Forbidden`.
