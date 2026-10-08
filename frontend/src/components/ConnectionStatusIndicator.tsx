import { useWebSocket, ConnectionStatus } from "@/contexts/WebSocketContext";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/Tooltip";

const statusConfig: Record<ConnectionStatus, { color: string; label: string }> = {
  CONNECTING: { color: "bg-yellow-500", label: "Connecting..." },
  OPEN: { color: "bg-green-500", label: "Connected" },
  CLOSING: { color: "bg-yellow-500", label: "Closing..." },
  CLOSED: { color: "bg-red-500", label: "Disconnected" },
  RECONNECTING: { color: "bg-yellow-500 animate-pulse", label: "Reconnecting..." },
};

export const ConnectionStatusIndicator = () => {
  const { connectionStatus } = useWebSocket();
  const config = statusConfig[connectionStatus];

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger>
          <div className={`h-3 w-3 rounded-full transition-colors ${config.color}`} />
        </TooltipTrigger>
        <TooltipContent>
          <p>{config.label}</p>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
};
