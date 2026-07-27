import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { Type } from "typebox";

function resultText(stdout: string, fallback: string): string {
  try {
    const value = JSON.parse(stdout) as { message?: string };
    return value.message
      ? `${value.message}\n\n${stdout.trim()}`
      : stdout.trim() || fallback;
  } catch {
    return stdout.trim() || fallback;
  }
}

export default function piWorkers(pi: ExtensionAPI): void {
  // Managed workers inherit this launcher-owned marker. They implement or review
  // work; orchestration tools are reserved for the parent orchestrator process.
  if (process.env.PI_WORKER_NAME) return;

  pi.registerTool({
    name: "spawn_pi_worker",
    label: "Spawn Pi worker",
    description:
      "Create an isolated Treehouse worktree and branch, open a named Herdr tab, and start Pi in it. " +
      "Prompt omitted starts an empty session; prompt supplied is sent as a delegated kickoff.",
    promptSnippet:
      "Start a visible Pi worker in an isolated Treehouse worktree and Herdr tab",
    parameters: Type.Object({
      repository: Type.Optional(
        Type.String({
          description:
            "Registered repository name; omit to use the configured default",
        }),
      ),
      name: Type.String({
        description: "Concise unique kebab-case worker and lease name",
      }),
      label: Type.String({
        description: "Human-readable Herdr tab and Pi session label",
      }),
      prompt: Type.Optional(
        Type.String({
          description: "Initial kickoff prompt; omit for an empty Pi session",
        }),
      ),
      model: Type.Optional(
        Type.String({ description: "Optional Pi provider/model selector" }),
      ),
      focus: Type.Optional(
        Type.Boolean({ description: "Focus the new tab; defaults to false" }),
      ),
    }),
    async execute(_toolCallId, params, signal) {
      const args = [
        "start",
        "--name",
        params.name,
        "--label",
        params.label,
        params.focus ? "--focus" : "--no-focus",
      ];
      if (params.repository) args.push("--repo", params.repository);
      if (params.model) args.push("--model", params.model);
      if (params.prompt) args.push("--prompt", params.prompt);
      const result = await pi.exec("pi-worker", args, {
        signal,
        timeout: 120_000,
      });
      if (result.code !== 0) {
        throw new Error(
          result.stderr.trim() || result.stdout.trim() || "pi-worker failed",
        );
      }
      return {
        content: [
          {
            type: "text",
            text: resultText(result.stdout, "Pi worker started"),
          },
        ],
        details: { stdout: result.stdout, stderr: result.stderr },
      };
    },
  });

  pi.registerTool({
    name: "list_pi_workers",
    label: "List Pi workers",
    description:
      "List recorded Pi workers with conservative Herdr/Pi liveness, Git, lease, and PR evidence. Output is bounded; labels never authorize mutation.",
    promptSnippet: "List recorded workers and conservative live status",
    promptGuidelines: [
      "Use list_pi_workers or inspect_pi_worker for worker awareness; do not continuously poll or infer authority from labels.",
    ],
    parameters: Type.Object({}),
    async execute(_toolCallId, _params, signal) {
      const result = await pi.exec("pi-worker", ["status"], {
        signal,
        timeout: 20_000,
      });
      if (result.code !== 0)
        throw new Error(result.stderr.trim() || "pi-worker status failed");
      return {
        content: [
          {
            type: "text",
            text: result.stdout.trim() || "No recorded Pi workers.",
          },
        ],
        details: { stdout: result.stdout },
      };
    },
  });

  pi.registerTool({
    name: "inspect_pi_worker",
    label: "Inspect Pi worker",
    description:
      "Inspect one exact recorded worker: registry identity, Herdr/Pi state, bounded recent pane output, Git, lease, and reliable PR evidence.",
    promptSnippet: "Inspect one exact recorded worker",
    parameters: Type.Object({
      name: Type.String({
        description: "Exact worker name returned by spawn_pi_worker",
      }),
    }),
    async execute(_toolCallId, params, signal) {
      const result = await pi.exec("pi-worker", ["inspect", params.name], {
        signal,
        timeout: 30_000,
      });
      if (result.code !== 0)
        throw new Error(result.stderr.trim() || "pi-worker inspect failed");
      return {
        content: [{ type: "text", text: result.stdout.trim() }],
        details: { stdout: result.stdout },
      };
    },
  });

  pi.registerTool({
    name: "send_pi_worker_follow_up",
    label: "Send Pi worker follow-up",
    description:
      "Type one short follow-up into an exact recorded worker pane and submit it once. Never retries Enter; verification may be inconclusive.",
    promptSnippet: "Send a short follow-up to an exact worker once",
    parameters: Type.Object({
      name: Type.String({ description: "Exact recorded worker name" }),
      text: Type.String({
        description: "Short follow-up text (maximum 2000 characters)",
      }),
    }),
    async execute(_toolCallId, params, signal) {
      const result = await pi.exec(
        "pi-worker",
        ["follow-up", params.name, params.text],
        { signal, timeout: 30_000 },
      );
      if (result.code !== 0)
        throw new Error(result.stderr.trim() || "worker follow-up failed");
      return {
        content: [
          {
            type: "text",
            text: resultText(result.stdout, "Follow-up submitted"),
          },
        ],
        details: { stdout: result.stdout },
      };
    },
  });

  pi.registerTool({
    name: "focus_pi_worker",
    label: "Focus Pi worker",
    description:
      "Focus/take over the tab for one exact recorded worker. Does not create or return any resource.",
    parameters: Type.Object({
      name: Type.String({ description: "Exact recorded worker name" }),
    }),
    async execute(_toolCallId, params, signal) {
      const result = await pi.exec("pi-worker", ["focus", params.name], {
        signal,
        timeout: 20_000,
      });
      if (result.code !== 0)
        throw new Error(result.stderr.trim() || "worker focus failed");
      return {
        content: [
          { type: "text", text: resultText(result.stdout, "Worker focused") },
        ],
        details: { stdout: result.stdout },
      };
    },
  });

  pi.registerTool({
    name: "resume_pi_worker",
    label: "Resume Pi worker",
    description:
      "Resume an exited Pi only in its exact recorded pane and only when a durable exact session path was reconciled. Missing or ambiguous identities stop safely.",
    parameters: Type.Object({
      name: Type.String({ description: "Exact recorded worker name" }),
    }),
    async execute(_toolCallId, params, signal) {
      const result = await pi.exec("pi-worker", ["resume", params.name], {
        signal,
        timeout: 30_000,
      });
      if (result.code !== 0)
        throw new Error(result.stderr.trim() || "worker resume failed");
      return {
        content: [
          {
            type: "text",
            text: resultText(result.stdout, "Exact session resume submitted"),
          },
        ],
        details: { stdout: result.stdout },
      };
    },
  });

  pi.registerTool({
    name: "restore_pi_workers",
    label: "Restore Pi workers",
    description:
      "Recreate missing managed worker tabs from exact durable registry, session, worktree, branch, and lease identities. Existing exact workers are left alone; ambiguity stops safely.",
    promptSnippet: "Restore missing managed workers from durable records",
    parameters: Type.Object({
      workspace: Type.Optional(
        Type.String({
          description: "Herdr workspace id; omit to use the caller's workspace",
        }),
      ),
    }),
    async execute(_toolCallId, params, signal) {
      const args = ["restore-all"];
      if (params.workspace) args.push("--workspace", params.workspace);
      const result = await pi.exec("pi-worker", args, {
        signal,
        timeout: 120_000,
      });
      if (result.code !== 0) {
        throw new Error(
          result.stderr.trim() ||
            result.stdout.trim() ||
            "managed worker restore failed",
        );
      }
      return {
        content: [
          {
            type: "text",
            text: resultText(result.stdout, "Managed workers restored"),
          },
        ],
        details: { stdout: result.stdout, stderr: result.stderr },
      };
    },
  });

  pi.registerTool({
    name: "return_pi_worker",
    label: "Return Pi worker",
    description:
      "Close a recorded worker tab and return its Treehouse lease. Refuses dirty worktrees by default; force discards uncommitted changes and requires interactive human confirmation.",
    parameters: Type.Object({
      name: Type.String({
        description: "Worker name returned by spawn_pi_worker",
      }),
      force: Type.Optional(
        Type.Boolean({
          description:
            "Discard uncommitted changes after interactive human confirmation; defaults to false",
        }),
      ),
    }),
    async execute(_toolCallId, params, signal, _onUpdate, ctx) {
      const args = ["return", params.name];
      if (params.force) {
        if (!ctx.hasUI) {
          throw new Error(
            "Force return requires interactive human confirmation; preserve the worker or retry in an interactive orchestrator session.",
          );
        }
        const confirmed = await ctx.ui.confirm(
          "Discard worker changes?",
          `Force-return '${params.name}' and discard its uncommitted changes?`,
          { signal, timeout: 30_000 },
        );
        if (!confirmed) throw new Error("Force return was not confirmed.");
        args.push("--force");
      }
      const result = await pi.exec("pi-worker", args, {
        signal,
        timeout: 60_000,
      });
      if (result.code !== 0) {
        throw new Error(
          result.stderr.trim() ||
            result.stdout.trim() ||
            "pi-worker return failed",
        );
      }
      return {
        content: [
          {
            type: "text",
            text: resultText(result.stdout, "Pi worker returned"),
          },
        ],
        details: { stdout: result.stdout, stderr: result.stderr },
      };
    },
  });
}
