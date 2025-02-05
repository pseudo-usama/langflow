import useFlowStore from "@/stores/flowStore";
import { GetCodeType } from "@/types/tweaks";

/**
 * Function to generate JavaScript code for interfacing with an API using the LangflowClient class.
 * @param {string} flowId - The id of the flow.
 * @param {boolean} isAuth - Whether the API requires authentication.
 * @param {any[]} tweaksBuildedObject - Customizations applied to the flow.
 * @param {string} [endpointName] - Optional endpoint name.
 * @returns {string} - The JavaScript code as a string.
 */
export default function getJsApiCode({
  flowId,
  isAuth,
  tweaksBuildedObject,
  endpointName,
  activeTweaks,
}: GetCodeType): string {
  let tweaksString = "{}";
  if (tweaksBuildedObject)
    tweaksString = JSON.stringify(tweaksBuildedObject, null, 8);
  const inputs = useFlowStore.getState().inputs;
  const outputs = useFlowStore.getState().outputs;
  const hasChatInput = inputs.some((input) => input.type === "ChatInput");
  const hasChatOutput = outputs.some((output) => output.type === "ChatOutput");

  return `${activeTweaks ? "" : 'let inputValue = ""; // Insert input value here\n\n'}fetch(
  "${window.location.protocol}//${window.location.host}/api/v1/run/${endpointName || flowId}?stream=false",
  {
    method: "POST",
    headers: {
      "Authorization": "Bearer <TOKEN>",
      "Content-Type": "application/json",${isAuth ? '\n\t\t\t"x-api-key": <your api key>' : ""}
    },
    body: JSON.stringify({${activeTweaks ? "" : "\n\t\t\tinput_value: inputValue, "}
      output_type: ${hasChatOutput ? '"chat"' : '"text"'},
      input_type: ${hasChatInput ? '"chat"' : '"text"'},
      tweaks: ${tweaksString}
    }),
  },
)
  .then(res => res.json())
  .then(data => console.log(data))
  .catch(error => console.error('Error:', error));
`;
}

export function getNewJsApiCode({
  streaming,
  flowId,
  isAuthenticated,
  input_value,
  input_type,
  output_type,
  tweaksObject,
  activeTweaks,
}: {
  streaming: boolean;
  flowId: string;
  isAuthenticated: boolean;
  input_value: string;
  input_type: string;
  output_type: string;
  tweaksObject: any;
  activeTweaks: boolean;
}): string {
  // get the host from the window location
  const host = window.location.host;
  // get the protocol from the window location
  const protocol = window.location.protocol;
  // get the api url
  const apiUrl = `${protocol}//${host}/api/v1/run/${flowId}`;

  // Convert tweaks object to a string if it exists and is active
  const tweaksString =
    tweaksObject && activeTweaks ? JSON.stringify(tweaksObject, null, 2) : "{}";

  return `const payload = {
    "input_value": "${input_value}",
    "output_type": "${output_type}",
    "input_type": "${input_type}"${
      activeTweaks && tweaksObject
        ? `,
    "tweaks": ${tweaksString}`
        : ""
    }
};
const options = {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json'${isAuthenticated ? ',\n        "x-api-key": "YOUR-API-KEY"' : ""}
    },
    body: JSON.stringify(payload)
};
fetch('${apiUrl}?stream=${streaming}')
    .then(response => response.json())
    .then(response => console.log(response))
    .catch(err => console.error(err));
    `;
}
