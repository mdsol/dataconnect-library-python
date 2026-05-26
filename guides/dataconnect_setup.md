# DataConnect Python Library Setup

This document is intended for first-time end-users.

## Prerequisites
### Environment
* Python 3.13
  * Should automatically include `pip` and `venv` (Python Virtual Environment)
* IDE of choice - `Visual Studio Code`, `PyCharm` etc. with `Jupyter` plugin

### Credentials
* An iMedidata Account
* Access to **DataConnect**'s **Developer Center** and **Transformations** in iMedidata

*Note:* You will need a generated `User Token` from **Developer Center** to make any function calls in this library.

## Setup
* On your Terminal window of choice (`bash`, `zsh`, `iTerm`, `WSL`, `gitBash` etc), create a new directory and go to it.

  ```bash
  mkdir dataconnect && cd $_
  ```

* Create a Python Virtual Environment and Activate it. Depending on your setup, you may use the `python` command instead of `python3`.

  ```bash
  python3 -m venv ./.venv
  source ./.venv/bin/activate
  ```

  * To confirm that the virtual environment has been created and activated, simply enter `which python3` (or `which python`) and it should point to the `dataconnect/venv/bin` path. If not, run the above commands again.


* Run the following command to fetch the latest-released `dataconnect-library-python` package. In this example, version `1.0.0` is assumed to be the latest release:

  ```bash
  pip install git+https://github.com/mdsol/dataconnect-library-python.git@1.0.0
  ```

* If there are no errors in fetching the package, open the directory in your IDE. For example, run this for VS Code:

  ```bash
  code .
  ```

* Download the usage jupyter file and open it in the same IDE window.
