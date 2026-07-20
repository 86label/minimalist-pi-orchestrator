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
  pi.registerTool({
    name: "spawn_pi_worker",
    label: "Spawn Pi worker",
    description:
      "Create an isolated Treehouse worktree and branch, open a named Herdr tab, and start Pi in it. " +
      "Omit prompt for an empty human-led session; include prompt to delegate agreed work immediately.",
    promptSnippet:
      "Start a visible Pi worker in an isolated Treehouse worktree and Herdr tab",
    promptGuidelines: [
      "Use spawn_pi_worker when the user naturally asks to open a tab/session for work or to delegate discussed work; do not require a slash command or exact phrasing.",
      "For a human-led tab, omit spawn_pi_worker.prompt and normally set focus=true. For delegated work, provide a self-contained prompt and normally set focus=false.",
      "When delegating with spawn_pi_worker, include the objective, discussion decisions, constraints, acceptance criteria, and relevant work-catalog references without inventing requirements.",
      "Choose a concise unique kebab-case spawn_pi_worker.name and a short human-readable label. Omit repository to use the configured default unless the conversation clearly identifies another registered repository.",
    ],
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
          description:
            "Self-contained initial assignment; omit for an empty Pi session",
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
      "List recorded Pi workers, including worktrees, branches, and Git status.",
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
    name: "return_pi_worker",
    label: "Return Pi worker",
    description:
      "Close a recorded worker tab and return its Treehouse lease. Refuses dirty worktrees unless force is explicit.",
    promptGuidelines: [
      "Never set return_pi_worker.force=true unless the user explicitly asks to discard that worker's uncommitted changes.",
    ],
    parameters: Type.Object({
      name: Type.String({
        description: "Worker name returned by spawn_pi_worker",
      }),
      force: Type.Optional(
        Type.Boolean({
          description: "Discard uncommitted changes; defaults to false",
        }),
      ),
    }),
    async execute(_toolCallId, params, signal) {
      const args = ["return", params.name];
      if (params.force) args.push("--force");
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
