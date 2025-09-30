import { Bell } from "lucide-react";
import { Button } from "../../../components/ui/Button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuHeader,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "../../../components/ui/DropdownMenu";
import { useWebSocket } from "../../../contexts/WebSocketContext"; // Updated import
import { formatDistanceToNow } from 'date-fns';

export const NotificationBell = () => {
  const { notifications, unreadCount, markAllAsRead } = useWebSocket(); // Use the new hook

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
        <DropdownMenuHeader className="flex justify-between items-center">
          <DropdownMenuLabel>Notifications</DropdownMenuLabel>
          {unreadCount > 0 && (
            <Button variant="link" size="sm" onClick={markAllAsRead} className="p-0 h-auto">
              Mark all as read
            </Button>
          )}
        </DropdownMenuHeader>
        <DropdownMenuSeparator />
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
                  <p className="text-sm font-medium leading-none">
                    {notification.content}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {formatDistanceToNow(new Date(notification.created_at), { addSuffix: true })}
                  </p>
                </div>
              </DropdownMenuItem>
            ))
          )
        }
      </DropdownMenuContent>
    </DropdownMenu>
  );
};
