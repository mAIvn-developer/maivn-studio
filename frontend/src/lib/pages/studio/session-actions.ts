import type {
  BatchInvocationConfig,
  App,
  MessageAttachmentPayload,
  SendableMessageType,
  StructuredOutputConfig,
} from "$lib/types";

interface CreateStudioSessionActionsParams {
  getSelectedApp: () => { id: string } | null;
  selectApp: (appId: string) => void;
  addRecentApp: (app: App) => void;
  resetSession: () => void;
  startSession: (
    appId: string,
    message: string,
    options?: {
      variant?: string;
      messageType?: SendableMessageType;
      attachments?: MessageAttachmentPayload[];
      systemMessage?: string;
      structuredOutput?: StructuredOutputConfig;
      batch?: BatchInvocationConfig;
    },
  ) => void;
  sendMessage: (
    message: string,
    messageType?: SendableMessageType,
    structuredOutput?: StructuredOutputConfig,
    attachments?: MessageAttachmentPayload[],
    batch?: BatchInvocationConfig,
  ) => void;
  setMessageType: (type: SendableMessageType) => void;
  setPrivateData: (data: Record<string, unknown>) => void;
  setStructuredOutputConfig: (config: StructuredOutputConfig) => void;
  getSession: () => { is_active?: boolean } | null;
  endSession: () => Promise<void>;
  getShowEvents: () => boolean;
  setShowEvents: (value: boolean) => void;
  openDiscovery: () => void | Promise<void>;
}

export function createStudioSessionActions(params: CreateStudioSessionActionsParams) {
  function handleSelectApp(app: App) {
    params.resetSession();
    params.selectApp(app.id);
    params.addRecentApp(app);
  }

  function handleStart(
    message: string,
    options?: {
      variant?: string;
      messageType?: SendableMessageType;
      attachments?: MessageAttachmentPayload[];
      systemMessage?: string;
      structuredOutput?: StructuredOutputConfig;
      batch?: BatchInvocationConfig;
    },
  ) {
    const selectedApp = params.getSelectedApp();
    if (!selectedApp) return;
    params.startSession(selectedApp.id, message, options);
  }

  function handleSend(
    message: string,
    messageType?: SendableMessageType,
    structuredOutput?: StructuredOutputConfig,
    attachments?: MessageAttachmentPayload[],
    batch?: BatchInvocationConfig,
  ) {
    params.sendMessage(message, messageType, structuredOutput, attachments, batch);
  }

  function handleMessageTypeChange(type: SendableMessageType) {
    params.setMessageType(type);
  }

  function handleStructuredOutputChange(config: StructuredOutputConfig) {
    params.setStructuredOutputConfig(config);
  }

  function handlePrivateDataChange(data: Record<string, unknown>) {
    params.setPrivateData(data);
  }

  function handleNewThread() {
    if (params.getSession()?.is_active) {
      // Fire-and-forget: don't block UI reset on server acknowledgment.
      // resetSession() disconnects the WebSocket anyway, so the server
      // will detect the session end regardless of the API response.
      params.endSession().catch(() => {});
    }
    params.resetSession();
  }

  function handleCommandPaletteAction(actionId: string) {
    switch (actionId) {
      case "new-thread":
        handleNewThread();
        break;
      case "toggle-events":
        params.setShowEvents(!params.getShowEvents());
        break;
      case "scan-repo":
        params.openDiscovery();
        break;
    }
  }

  return {
    handleSelectApp,
    handleStart,
    handleSend,
    handleMessageTypeChange,
    handleStructuredOutputChange,
    handlePrivateDataChange,
    handleNewThread,
    handleCommandPaletteAction,
  };
}
