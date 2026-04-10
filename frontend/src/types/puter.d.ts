export {};

declare global {
  interface PuterUI {
    authenticateWithPuter: () => Promise<void>;
  }

  interface PuterSDK {
    authToken?: string;
    ui: PuterUI;
  }

  interface Window {
    puter?: PuterSDK;
  }
}
