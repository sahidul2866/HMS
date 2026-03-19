declare global {
  interface Window {
    __HMS_CONFIG__?: {
      apiBaseUrl?: string;
    };
  }
}

export {};
