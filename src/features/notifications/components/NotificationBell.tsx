import { Bell } from "lucide-react";
import { Button } from "@/components/ui/Button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/DropdownMenu";
// DropdownMenuHeader seems to be missing from the standard shadcn dropdown or custom, 
// using DropdownMenuLabel as fallback or checking file
import { useWebSocket } from "@/contexts/WebSocketContext";
import { formatDistanceToNow } from 'date-fns';

export const NotificationBell = () => {
  const { notifications, unreadCount, markAllAsRead } = useWebSocket();

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="outline" size="icon" className="relative">
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
          <DropdownMenuLabel className="p-0">Notifications</DropdownMenuLabel>
          {unreadCount > 0 && (
            <Button variant="link" size="sm" onClick={markAllAsRead} className="p-0 h-auto text-[10px]">
              Mark all as read
            </Button>
          )}
        </div>
        <DropdownMenuSeparator />
        <div className="max-h-96 overflow-y-auto">
          {
            notifications.length === 0 ? (
              <p className="py-4 text-center text-sm text-muted-foreground">No notifications yet.</p>
            ) : (
              notifications.map((notification) => (
                <DropdownMenuItem key={notification.id} className="flex items-start gap-2">
                  {!notification.read && (
                    <span className="flex h-2 w-2 translate-y-1 rounded-full bg-sky-500" />
                  )}
                  <div className={`flex-1 space-y-1 ${notification.read ? 'text-muted-foreground' : ''}`}>
                    <p className="text-sm font-medium leading-tight">
                      {notification.content}
                    </p>
                    <p className="text-[10px] text-muted-foreground">
                      {formatDistanceToNow(new Date(notification.created_at), { addSuffix: true })}
                    </p>
                  </div>
                </DropdownMenuItem>
              ))
            )
          }
        </div>
      </DropdownMenuContent>
    </DropdownMenu>
  );
};