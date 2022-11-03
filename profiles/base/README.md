# galaxy_base

## Usage

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
- `UPDATE_UI`
    - Description: Download the precompiled UI from github
    - Options:
        - 0: don't download the UI.
        - 1: download the latest version of the UI.
    - Default: 1
- `SETUP_TEST_DATA`
    - Description: Set up the data required to run the integration tests
    - Options:
        - 0: don't set up test data.
        - 1: set up test data.
    - Default: 0