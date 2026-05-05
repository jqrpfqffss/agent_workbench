# Test Failure Triage

Separate failures by layer before editing code.

## 1. Test Design Problem

Symptoms:

- the expected behavior is vague
- the probe does not match the user's goal
- the assertion targets an unstable string or value

Action: fix the coverage matrix, probe command, or assertion target first.

## 2. Probe Or Observability Problem

Symptoms:

- `uart exec` does not send the command that triggers the feature
- `diag exec` request does not match the current protocol
- `monitor probe` reads the wrong or missing symbol

Action: correct the command, request, monitor item, or observability path before changing production code.

## 3. Source Behavior Problem

Symptoms:

- the test design is clear
- the probe triggers the behavior
- runtime evidence shows the behavior violates the expected result

Action: modify production code, then rebuild and rerun the runtime evidence path.

## 4. Environment Or Hardware Blocker

Symptoms:

- `doctor` fails
- `flash` fails
- UART receives no bytes
- monitor cannot sample

Action: stop and report the blocker. Do not label it as a firmware test failure.

## Decision Order

Ask in order:

1. Is the test design correct?
2. Does the probe trigger the behavior?
3. Is runtime evidence available?
4. Does the source behavior actually violate the expected result?
