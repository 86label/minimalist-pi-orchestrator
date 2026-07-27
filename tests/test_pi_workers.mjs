import assert from "node:assert/strict";
import test from "node:test";

import piWorkers from "../src/pi-workers.ts";

function loadTools(workerName) {
  const previous = process.env.PI_WORKER_NAME;
  if (workerName === undefined) delete process.env.PI_WORKER_NAME;
  else process.env.PI_WORKER_NAME = workerName;

  const tools = [];
  const execCalls = [];
  try {
    piWorkers({
      registerTool(tool) {
        tools.push(tool);
      },
      async exec(command, args) {
        execCalls.push([command, args]);
        return { code: 0, stdout: "{}\n", stderr: "" };
      },
    });
  } finally {
    if (previous === undefined) delete process.env.PI_WORKER_NAME;
    else process.env.PI_WORKER_NAME = previous;
  }
  return { tools, execCalls };
}

test("orchestrator environment registers typed worker lifecycle and awareness tools", () => {
  const { tools } = loadTools();
  assert.deepEqual(
    tools.map((tool) => tool.name),
    [
      "spawn_pi_worker",
      "list_pi_workers",
      "inspect_pi_worker",
      "send_pi_worker_follow_up",
      "focus_pi_worker",
      "resume_pi_worker",
      "restore_pi_workers",
      "return_pi_worker",
    ],
  );

  const spawn = tools[0];
  assert.equal(spawn.promptGuidelines, undefined);
  assert.match(spawn.description, /prompt omitted|omit prompt/i);
  assert.match(spawn.description, /prompt supplied|include prompt/i);
  assert.match(spawn.parameters.properties.repository.description, /default/i);
  assert.match(
    spawn.parameters.properties.focus.description,
    /defaults to false/i,
  );
  assert.doesNotMatch(
    spawn.description,
    /catalog|acceptance criteria|review|PR lifecycle/i,
  );

  const followUp = tools.find(
    (tool) => tool.name === "send_pi_worker_follow_up",
  );
  assert.match(followUp.description, /once|never retries/i);
  assert.match(followUp.parameters.properties.name.description, /exact/i);

  const restore = tools.find((tool) => tool.name === "restore_pi_workers");
  assert.match(restore.description, /exact durable|ambiguity/i);

  const returned = tools.find((tool) => tool.name === "return_pi_worker");
  assert.equal(returned.promptGuidelines, undefined);
  assert.match(returned.description, /interactive human confirmation/i);
});

test("managed-worker environment registers no orchestration tools", () => {
  const { tools } = loadTools("implementation-worker");
  assert.deepEqual(tools, []);
});

test("force return fails closed without interactive human confirmation", async () => {
  const { tools, execCalls } = loadTools();
  const returned = tools.find((tool) => tool.name === "return_pi_worker");

  await assert.rejects(
    returned.execute(
      "call-1",
      { name: "dirty-worker", force: true },
      undefined,
      undefined,
      { hasUI: false, ui: {} },
    ),
    /requires interactive human confirmation/i,
  );
  assert.deepEqual(execCalls, []);
});
