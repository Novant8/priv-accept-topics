# Generate Devtools Python Bindings

This folder contains the necessary scripts to generate the Python bindings for the Chrome Devtools Protocol, related to a specific version of Chromium.

## How to generate the bindings

### Download the necessary files

There are two [PDL](https://github.com/google/pdl) files needed to download:

* `browser_protocol.pdl`, containing the protocol definition for browser automation.
    * Download at the following link: `https://raw.githubusercontent.com/chromium/chromium/<CHROMIUM_VERSION_NUMBER>/third_party/blink/public/devtools_protocol/browser_protocol.pdl`

* `js_protocol.pdl`, which defines the protocol to debug the JavaScripts executed by the browser.
    * Figure out what is the v8 version used by Chromium, by going to this link: `https://github.com/chromium/chromium/blob/<CHROMIUM_VERSION_NUMBER>/DEPS`. Look for the `v8_revision` property (e.g. `6ac54d1cdc0e26ab1d73a740fd9ec6a9698e39fd`).
    * With the v8 revision number, you can download the `js_protocol.pdl` at the following link: `https://github.com/v8/v8/raw/<V8_REVISION_NUMBER>/include/js_protocol.pdl`

### Run the scripts

Do the following steps in order:

1. Convert both the `.pdl` files to a JSON format:
```shell
python convert_protocol_to_json.py /path/to/browser_protocol.pdl /path/to/browser_protocol.json [--map_binary_to_string=true]
python convert_protocol_to_json.py /path/to/js_protocol.pdl /path/to/js_protocol.json [--map_binary_to_string=true]
```

2. Generate the Python bindings from the JSON protocol files:
```shell
python generate.py /path/to/browser_protocol.json /path/to/js_protocol.json /path/to/output_bindings
```

### Copy/Move the generated bindings to the Selenium package folder

```shell
cp /path/to/output_bindings /path/to/python/site-packages/selenium/webdriver/common/devtools/v<NUMBER>
```

`NUMBER` is the major Chromium version (e.g., if the Chromium version is `122.0.6261.128`, then `NUMBER` is `122`.)

## Credit

The scripts present in this folder are the same present in the [Selenium repository](https://github.com/SeleniumHQ/selenium/tree/trunk/common/devtools):

* [`convert_protocol_to_json.py` and `pdl.py`](https://github.com/SeleniumHQ/selenium/tree/88479dcabfadd4e39dc3f4f17eb6a1d75f00edd5/common/devtools)

* [`generate.py`](https://github.com/SeleniumHQ/selenium/blob/88479dcabfadd4e39dc3f4f17eb6a1d75f00edd5/py/generate.py#L23)