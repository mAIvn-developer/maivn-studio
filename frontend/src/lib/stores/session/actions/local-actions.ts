import type { ChatFlowFilters, InterruptData, MemoryConfig, SendableMessageType } from "$lib/types";

interface CreateSessionLocalActionsParams {
  setMessageTypeState: (type: SendableMessageType) => void;
  setPrivateDataState: (data: Record<string, unknown>) => void;
  getFilters: () => ChatFlowFilters;
  setFiltersState: (filters: ChatFlowFilters) => void;
  setErrorState: (error: string | null) => void;
  setMemoryConfigState: (config: MemoryConfig) => void;
  getPendingInterrupts: () => InterruptData[];
  getAllInterrupts: () => InterruptData[];
}

export function createSessionLocalActions(params: CreateSessionLocalActionsParams) {
  function setMessageType(type: SendableMessageType) {
    params.setMessageTypeState(type);
  }

  function setPrivateData(data: Record<string, unknown>) {
    params.setPrivateDataState(data);
  }

  function setFilters(newFilters: Partial<ChatFlowFilters>) {
    params.setFiltersState({ ...params.getFilters(), ...newFilters });
  }

  function clearError() {
    params.setErrorState(null);
  }

  function setMemoryConfigAction(config: MemoryConfig) {
    params.setMemoryConfigState(config);
  }

  return {
    setMessageType,
    setPrivateData,
    setFilters,
    clearError,
    setMemoryConfigAction,
    getPendingInterrupts: params.getPendingInterrupts,
    getAllInterrupts: params.getAllInterrupts,
  };
}
