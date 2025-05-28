// Adapted from https://github.com/ua-reduction/ua-client-hints-crawler/blob/ae68255322eaf23e7d06e81798bcd8c150bb7961/helpers/fingerprintDetection.js

(function() {
  const frameUrl = document.location.href
  const MAX_NUM_CALLS_TO_INTERCEPT = 100;
  const STACK_LINE_REGEXP = /(\()?(http[^)]+):[0-9]+:[0-9]+(\))?/;
  let accessCounts = {};  // keep the access and call counts for each property and function
  const ENABLE_CONSOLE_LOGS = false;
  const console_log = function() {
    if (ENABLE_CONSOLE_LOGS){
      console.log.apply(console, arguments);
    }
  };
  const getSourceFromStack = function() {
    const stack = new Error().stack.split("\n");
    stack.shift();  // remove our own intercepting functions from the stack
    stack.shift();
    const res = stack[1].match(STACK_LINE_REGEXP);
    return res ? res[2] : "UNKNOWN_SOURCE";
  }
  const getElementFromType = function (elementType) {
    const levels = typeof elementType === "string" ? elementType.split(".") : [];
    let element = globalThis;
    console_log(levels);
    for (const level of levels) {
      if (typeof element === "undefined") {
        console_log(`Cannot find element ${level} in ${elementType}`);
        return;
      }
      element = element[level];
      if (typeof element === "function") {
        element = element.prototype;
      }
    }
    return element;
  }

  const interceptFunctionCall = function (elementType, funcName, funcFilter) {
    // save the original function using a closure
    const element = getElementFromType(elementType);
    if (typeof element === "undefined") {
      return;
    }
    const calledFunc = elementType ? `${elementType}.${funcName}` : funcName
    console_log(`Intercepting ${calledFunc}`);
    const origFunc = element[funcName];
    // overwrite the object method with our own
    Object.defineProperty(element, funcName, {
      value: function () {
        // execute the original function
        let exception = undefined, retVal = undefined;
        try {
          retVal = origFunc.apply(this, arguments);
        } catch (e) {
          exception = e;
        }
        // check and enforce the limits
        // increment the call countl init if needed
        accessCounts[calledFunc] = (accessCounts[calledFunc] || 0) + 1;
        const callCnt = accessCounts[calledFunc];  // just a shorthand
        if (callCnt >= MAX_NUM_CALLS_TO_INTERCEPT) {
          console_log(`Reached max number of calls for ${calledFunc}: ${callCnt}`);
          // revert the function to its original state
          Object.defineProperty(element, funcName, {
            value: function () {return origFunc.apply(this, arguments);}
          });
          if (exception) {
            // if the original function threw an exception, rethrow it
            console_log(`Throwing original exception from ${calledFunc}: ${exception}`);
            throw exception;
          }
          return retVal;
        }
        // we still haven't reached the limit; we intercept the call
        console_log(`Intercepted call to ${calledFunc} ${callCnt} times`);
        const source = getSourceFromStack();
        const callDetails = {
          description: calledFunc,
          accessType: "call",
          args: arguments,
          retVal,
          exception,
          source,
          frameUrl
        };
        // register function call event only if it satisfies the given filter (if any)
        if (typeof funcFilter !== "function" || funcFilter(callDetails)) {
          console_log(`Calling calledAPIEvent with ${JSON.stringify(callDetails)}`);
          // send the call details to the node context
          // @ts-ignore
          globalThis.calledAPIEvent(JSON.stringify(callDetails));
        }
        if (exception) {
          // if the original function threw an exception, rethrow it
          throw exception;
        }
        return retVal;
      }
    });
  };
  const interceptPropAccess = function (elementType, propertyName) {
    // Limit api calls to intercept
    // save the original property descriptor using a closure
    const element = getElementFromType(elementType);
    if (typeof element === "undefined") {
      console_log(`Cannot find element ${level} in ${elementType}`);
      return;
    }
    const origObjPropDesc = Object.getOwnPropertyDescriptor(
      element,
      propertyName
    );
    // log property name
    const accessedProp = elementType ? `${elementType}.${propertyName}` : propertyName;
    Object.defineProperty(element, propertyName, {
      enumerable: true,
      configurable: true,
      get: function () {
        let returnVal = origObjPropDesc.get.call(this);
        // check and enforce the limits
        accessCounts[accessedProp] = (accessCounts[accessedProp] || 0) + 1;
        const accessCnt = accessCounts[accessedProp];  // just a shorthand
        if (accessCnt >= MAX_NUM_CALLS_TO_INTERCEPT) {
          console_log(`Reached max number of accesses for ${accessedProp}: ${accessCnt} `);
          // revert the setter to its original state
          Object.defineProperty(element, propertyName, {
            get: function () {return origObjPropDesc.get.call(this);}
          });
          return;
        }
        // we still haven't reached the limit; we intercept the access
        console_log(`Intercepted property access (get) ${accessedProp} (${accessCnt} times)`);
        const source = getSourceFromStack();
        const callDetails = {
          description: accessedProp,
          accessType: "get",
          args: "",
          source,
          frameUrl
        };
        // send the call details to the node context
        // @ts-ignore
        globalThis.calledAPIEvent(JSON.stringify(callDetails));
        return returnVal;
      },  // TODO
      set: function (value) {
        // set the given value using the original property setter
        origObjPropDesc.set.call(this, value);

        // check and enforce the limits
        accessCounts[accessedProp] = (accessCounts[accessedProp] || 0) + 1;
        const accessCnt = accessCounts[accessedProp];  // just a shorthand
        if (accessCnt >= MAX_NUM_CALLS_TO_INTERCEPT) {
          console_log(`Reached max number of accesses for ${accessedProp}: ${accessCnt} `);
          // revert the setter to its original state
          Object.defineProperty(element, propertyName, {
            set: function () {return origObjPropDesc.set.call(this, value);}
          });
          return;
        }
        // we still haven't reached the limit; we intercept the access
        console_log(`Intercepted property access (set) ${accessedProp} (${accessCnt} times)`);
        const source = getSourceFromStack();
        const callDetails = {
          description: accessedProp,
          accessType: "set",
          args: value,
          source,
          frameUrl
        };
        // send the call details to the node context
        // @ts-ignore
        globalThis.calledAPIEvent(JSON.stringify(callDetails));
      },
    });
  };
  
  const api_calls = [
    {
      "elementType": "SharedStorage",
      "funcNames": [
          "append",
          "get",
          "set",
          "clear",
          "delete",
          "batchUpdate",
          "createWorklet"
      ],
      "propNames": []
    },
    {
      "elementType": "SharedStorageWorklet",
      "funcNames": [
          "addModule"
      ],
      "propNames": []
    },
    {
        "elementType": "Navigator",
        "funcNames": [
            "joinAdInterestGroup",
            "updateAdInterestGroups",
            "leaveAdInterestGroup",
            "runAdAuction",
            "hasPrivateToken",
            "hasRedemptionRecord"
        ],
        "propNames": []
    },
    {
        "elementType": "Document",
        "funcNames": [
            "browsingTopics",
            "requestStorageAccess",
            "requestStorageAccessFor"
        ],
        "propNames": []
    },
    {
      "elementType": undefined,
      "funcNames": [
        "fetch",
        "open"
      ],
      "propNames": [],
      "funcFilter": function (callDetails) {
        switch (callDetails["description"]) {
          case "fetch":
            // register only those fetch calls thet include options relevant to the Privacy Sandbox
            const FETCH_PS_PROPERTIES = [ "browsingTopics", "attributionReporting", "privateToken", "sharedStorageWritable" ];
            const args = callDetails["args"];
            return typeof args[1] === "object" && FETCH_PS_PROPERTIES.some(prop => args[1].hasOwnProperty(prop));
          case "open":
            return args.some(arg => typeof arg === "string" && arg.includes("attributionsrc"))
        }
      }
    },
    {
      "elementType": "CredentialsContainer",
      "funcNames": [
        "get",
      ],
      "propNames": []
    }
  ];

  for (const { elementType, funcNames, propNames, funcFilter } of api_calls) {
    for (const funcName of funcNames)
      interceptFunctionCall(elementType, funcName, funcFilter);
    for (const propName of propNames)
      interceptPropAccess(elementType, propName);
  }
})();