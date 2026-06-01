const form = document.getElementById("api-form");
const methodSelect = document.getElementById("api-method");
const endpointInput = document.getElementById("api-endpoint");
const bodyInput = document.getElementById("api-body");
const responseOutput = document.getElementById("response-output");
const responseStatus = document.getElementById("response-status");
const responseTime = document.getElementById("response-time");
const responseSize = document.getElementById("response-size");
const baseDisplay = document.getElementById("api-base");
const clearButton = document.getElementById("clear-response");
const refreshAll = document.getElementById("refresh-all");

baseDisplay.textContent = window.location.origin;

const quickButtons = document.querySelectorAll(".action");
const resourceSections = document.querySelectorAll(".resource");

function normalizeEndpoint(value) {
    const trimmed = value.trim();
    if (!trimmed) {
        return "";
    }
    if (trimmed.startsWith("http://") || trimmed.startsWith("https://")) {
        return trimmed;
    }
    if (trimmed.startsWith("/")) {
        return trimmed;
    }
    return `/${trimmed}`;
}

function updateResponseMeta(statusText, timeText, sizeText) {
    responseStatus.textContent = `Status: ${statusText}`;
    responseTime.textContent = `Time: ${timeText}`;
    responseSize.textContent = `Size: ${sizeText}`;
}

async function callApi({ method, endpoint, body }) {
    const url = normalizeEndpoint(endpoint);
    if (!url) {
        throw new Error("Missing endpoint.");
    }

    const options = { method };
    if (body !== null && body !== undefined) {
        options.headers = { "Content-Type": "application/json" };
        options.body = JSON.stringify(body, null, 2);
    }

    const start = performance.now();
    const response = await fetch(url, options);
    const elapsed = Math.round(performance.now() - start);
    const contentType = response.headers.get("content-type") || "";
    const isJson = contentType.includes("application/json");
    const data = isJson ? await response.json() : await response.text();
    const pretty = isJson ? JSON.stringify(data, null, 2) : String(data);

    return {
        ok: response.ok,
        status: response.status,
        elapsed,
        pretty,
        data,
    };
}

async function sendRequest({ method, endpoint, bodyText }) {
    const url = normalizeEndpoint(endpoint);
    if (!url) {
        responseOutput.textContent = "Enter an endpoint before sending.";
        updateResponseMeta("--", "--", "--");
        return;
    }

    let payload = null;
    const bodyTrimmed = bodyText.trim();
    const allowsBody = !["GET", "DELETE"].includes(method.toUpperCase());

    if (allowsBody && bodyTrimmed) {
        try {
            payload = JSON.parse(bodyTrimmed);
        } catch (error) {
            responseOutput.textContent = `Invalid JSON body: ${error.message}`;
            updateResponseMeta("Error", "--", "--");
            return;
        }
    }

    responseOutput.textContent = "Loading...";
    updateResponseMeta("Pending", "--", "--");

    try {
        const result = await callApi({ method, endpoint: url, body: payload });
        responseOutput.textContent = result.pretty || "(empty response)";
        updateResponseMeta(result.status, `${result.elapsed} ms`, `${result.pretty.length} chars`);
    } catch (error) {
        responseOutput.textContent = `Request failed: ${error.message}`;
        updateResponseMeta("Error", "--", "--");
    }
}

function getSectionParts(section) {
    return {
        status: section.querySelector("[data-status]"),
        output: section.querySelector("[data-output]"),
    };
}

function setSectionStatus(section, message, isError = false) {
    const { status } = getSectionParts(section);
    if (!status) {
        return;
    }
    status.textContent = message;
    status.classList.toggle("is-error", isError);
}

function setSectionOutput(section, message) {
    const { output } = getSectionParts(section);
    if (output) {
        output.textContent = message;
    }
}

function parseFieldValue(input, options) {
    if (input.type === "checkbox") {
        return {
            value: input.checked,
            hasValue: options.includeUnchecked || input.checked,
        };
    }

    const raw = input.value.trim();
    const type = input.dataset.type || "text";

    if (!raw) {
        if (type === "list") {
            return { value: [], hasValue: options.includeEmptyList };
        }
        return { value: null, hasValue: false };
    }

    if (type === "number") {
        const numberValue = Number(raw);
        if (Number.isNaN(numberValue)) {
            throw new Error(`Invalid number for ${input.dataset.field}.`);
        }
        return { value: numberValue, hasValue: true };
    }

    if (type === "integer") {
        const intValue = parseInt(raw, 10);
        if (Number.isNaN(intValue)) {
            throw new Error(`Invalid integer for ${input.dataset.field}.`);
        }
        return { value: intValue, hasValue: true };
    }

    if (type === "list") {
        const listValue = raw
            .split(",")
            .map((item) => item.trim())
            .filter(Boolean);
        return { value: listValue, hasValue: true };
    }

    if (type === "upper") {
        return { value: raw.toUpperCase(), hasValue: true };
    }

    return { value: raw, hasValue: true };
}

function collectPayload(form, options) {
    const inputs = Array.from(form.querySelectorAll("[data-field]"));
    const payload = {};

    for (const input of inputs) {
        const field = input.dataset.field;
        const { value, hasValue } = parseFieldValue(input, options);
        if (!hasValue) {
            continue;
        }
        payload[field] = value;
    }

    return payload;
}

async function loadSectionList(section, endpoint) {
    setSectionStatus(section, "Loading...", false);
    try {
        const result = await callApi({ method: "GET", endpoint, body: null });
        if (result.ok) {
            setSectionOutput(section, result.pretty || "(empty response)");
            setSectionStatus(section, `Loaded (${result.status}) in ${result.elapsed} ms`, false);
        } else {
            setSectionOutput(section, result.pretty || "(empty response)");
            setSectionStatus(section, `Error (${result.status})`, true);
        }
    } catch (error) {
        setSectionOutput(section, `Request failed: ${error.message}`);
        setSectionStatus(section, "Request failed", true);
    }
}

form.addEventListener("submit", (event) => {
    event.preventDefault();
    sendRequest({
        method: methodSelect.value,
        endpoint: endpointInput.value,
        bodyText: bodyInput.value,
    });
});

quickButtons.forEach((button) => {
    button.addEventListener("click", () => {
        methodSelect.value = button.dataset.method || "GET";
        endpointInput.value = button.dataset.endpoint || "";
        bodyInput.value = "";
        sendRequest({
            method: methodSelect.value,
            endpoint: endpointInput.value,
            bodyText: "",
        });
    });
});

clearButton.addEventListener("click", () => {
    responseOutput.textContent = "Waiting for a request...";
    updateResponseMeta("--", "--", "--");
});

resourceSections.forEach((section) => {
    const listButton = section.querySelector("[data-action='list']");
    const listEndpoint = listButton ? listButton.dataset.endpoint : section.dataset.listEndpoint;

    if (listButton && listEndpoint) {
        listButton.addEventListener("click", () => {
            loadSectionList(section, listEndpoint);
        });
    }

    const forms = section.querySelectorAll(".resource-form");
    forms.forEach((resourceForm) => {
        resourceForm.addEventListener("submit", async (event) => {
            event.preventDefault();
            const action = resourceForm.dataset.action;
            const endpoint = resourceForm.dataset.endpoint || "";
            const idField = resourceForm.dataset.idField;

            let method = "POST";
            if (action === "update") {
                method = "PATCH";
            } else if (action === "delete") {
                method = "DELETE";
            }

            let finalEndpoint = endpoint;
            if (idField) {
                const idInput = resourceForm.querySelector(`[data-field='${idField}']`);
                const idValue = idInput ? idInput.value.trim() : "";
                if (!idValue) {
                    setSectionStatus(section, "Missing ID for request.", true);
                    return;
                }
                finalEndpoint = `${endpoint}/${idValue}`;
            }

            let payload = null;
            if (action !== "delete") {
                try {
                    payload = collectPayload(resourceForm, {
                        includeUnchecked: action === "create",
                        includeEmptyList: action === "create",
                    });
                } catch (error) {
                    setSectionStatus(section, error.message, true);
                    return;
                }
            }

            setSectionStatus(section, "Sending...", false);
            try {
                const result = await callApi({ method, endpoint: finalEndpoint, body: payload });
                if (result.ok) {
                    setSectionStatus(section, `Success (${result.status})`, false);
                    if (listEndpoint) {
                        loadSectionList(section, listEndpoint);
                    }
                } else {
                    setSectionOutput(section, result.pretty || "(empty response)");
                    setSectionStatus(section, `Error (${result.status})`, true);
                }
            } catch (error) {
                setSectionOutput(section, `Request failed: ${error.message}`);
                setSectionStatus(section, "Request failed", true);
            }
        });
    });
});

if (refreshAll) {
    refreshAll.addEventListener("click", () => {
        resourceSections.forEach((section) => {
            const listEndpoint = section.dataset.listEndpoint;
            if (listEndpoint) {
                loadSectionList(section, listEndpoint);
            }
        });
    });
}
