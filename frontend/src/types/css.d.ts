/**
 * Style-import declarations.
 *
 * Next.js 15 ships no ambient `*.css` module declaration, and `next-env.d.ts`
 * is generated (its own header says not to edit it). Without these, tsserver
 * reports "Cannot find module or type declarations for side-effect import of
 * './globals.css'" on the `import "./globals.css"` in app/layout.tsx.
 *
 * The bare side-effect imports resolve to `void` because the bundler injects the
 * stylesheet — there is no runtime value to import. CSS Modules (`*.module.css`)
 * do export a class-name map, so those are typed as a string record.
 */

declare module "*.css" {
  const content: void;
  export default content;
}

declare module "*.module.css" {
  const classes: { readonly [key: string]: string };
  export default classes;
}

declare module "*.scss" {
  const content: void;
  export default content;
}

declare module "*.module.scss" {
  const classes: { readonly [key: string]: string };
  export default classes;
}
