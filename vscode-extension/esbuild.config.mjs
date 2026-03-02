import * as esbuild from "esbuild";

const watch = process.argv.includes("--watch");

/** @type {import('esbuild').BuildOptions} */
const baseOptions = {
  bundle: true,
  minify: !watch,
  sourcemap: watch,
  platform: "node",
  target: "es2020",
  format: "cjs",
  logLevel: "info",
};

// Extension client (runs in VS Code host)
const extensionBuild = esbuild.build({
  ...baseOptions,
  entryPoints: ["src/extension.ts"],
  outfile: "dist/extension.js",
  external: ["vscode"],
});

// Language Server (runs as child process)
const serverBuild = esbuild.build({
  ...baseOptions,
  entryPoints: ["src/server.ts"],
  outfile: "dist/server.js",
});

if (watch) {
  const extCtx = await esbuild.context({
    ...baseOptions,
    entryPoints: ["src/extension.ts"],
    outfile: "dist/extension.js",
    external: ["vscode"],
  });
  const srvCtx = await esbuild.context({
    ...baseOptions,
    entryPoints: ["src/server.ts"],
    outfile: "dist/server.js",
  });
  await extCtx.watch();
  await srvCtx.watch();
  console.log("Watching for changes...");
} else {
  await Promise.all([extensionBuild, serverBuild]);
}
