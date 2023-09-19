# Writing Docs

# test 123

Documentation is stored under the docs `docs/` directory in the [backend repository](https://github.com/ansible/galaxy_ng). Documentation built using [MkDocs](https://www.mkdocs.org/). Documentation is written using [Markdown](https://www.mkdocs.org/user-guide/writing-your-docs/#writing-with-markdown). Check out the [MkDocs documentation](https://www.mkdocs.org/getting-started/) for more information.

## Building the Docs Site Locally

1. Install the docs dependencies

    !!! Important
        We recommend creating a [python virtual environment](https://docs.python.org/3/library/venv.html) to install the documentation requirements in.

    ```bash
    make docs/install
    ```

2. Run the documentation service.

    ```bash
    make docs/serve
    ```

3. Navigate to http://localhost:8000 to view the docs site.


## Adding new pages

1. Create a new markdown file under `docs/`
2. Add your new file under the "nav" section in `mkdocs.yml` in the project root directory.