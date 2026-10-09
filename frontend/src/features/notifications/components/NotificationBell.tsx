import { Bell } from "lucide-react";
import { Link } from "react-router-dom";
import { formatDistanceToNow } from "date-fns";
import { ptBR } from "date-fns/locale";
import { Button } from "@/components/ui/Button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/DropdownMenu";
import { useWebSocket } from "@/contexts/WebSocketContext";

export const NotificationBell = () => {
  const { notifications, unreadCount, markAsRead, markAllAsRead } = useWebSocket();

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="outline"
          size="icon"
          className="relative"
          aria-label={unreadCount > 0 ? `Avisos (${unreadCount} não lidos)` : "Avisos"}
        >
          <Bell className="h-5 w-5" />
          {unreadCount > 0 && (
            <span className="absolute top-0 right-0 flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-red-500"></span>
            </span>
          )}
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-80">
        <div className="flex justify-between items-center p-4">
          <DropdownMenuLabel className="p-0">Avisos</DropdownMenuLabel>
          {unreadCount > 0 && (
            <Button variant="link" size="sm" onClick={markAllAsRead} className="p-0 h-auto text-[10px]">
              Marcar todos como lidos
            </Button>
          )}
        </div>
        <DropdownMenuSeparator />
        <div className="max-h-96 overflow-y-auto">
          {notifications.length === 0 ? (
            <p className="py-4 text-center text-sm text-muted-foreground">Nenhum aviso ainda.</p>
          ) : (
            notifications.map((notification) => (
              <DropdownMenuItem
                key={notification.id}
                className="flex items-start gap-2"
                onSelect={() => !notification.read && markAsRead(notification.id)}
              >
                {!notification.read && <span className="flex h-2 w-2 translate-y-1 rounded-full bg-sky-500" />}
                <div className={`flex-1 space-y-1 ${notification.read ? "text-muted-foreground" : ""}`}>
                  <p className="text-sm font-medium leading-tight">{notification.content}</p>
                  <p className="text-[10px] text-muted-foreground">
                    {formatDistanceToNow(new Date(notification.created_at), { addSuffix: true, locale: ptBR })}
                  </p>
                </div>
              </DropdownMenuItem>
            ))
          )}
        </div>
        <DropdownMenuSeparator />
        <DropdownMenuItem asChild>
          <Link to="/notifications" className="justify-center text-sm font-medium">
            Ver todos os avisos
          </Link>
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
};
