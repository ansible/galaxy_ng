# galaxy_base

## Usage

*Add a description detailing what this profile does and any extra instructions for using it.*

This provides the basic settings required to run Galaxy NG.

## Extra Variables

*List any extra variables that user's can configure in their .compose.env*

- `ENABLE_SIGNING`
    - Description: Enable or disable the signing service
    - Options:
        - 0: disable signing
        - 1: setup keyrings and create default signing service
        - 2: setup keyrings, but don't create a signing service
    - Default: 1