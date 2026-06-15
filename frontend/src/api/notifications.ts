import { api } from "./client";
import type { Paginated } from "./employees";

export interface NotificationRecord {
  id: string;
  event_key: string;
  title: string;
  body: string;
  level: "info" | "success" | "warning" | "error";
  level_display?: string;
  url?: string;
  entity_type?: string;
  entity_id?: string;
  is_read: boolean;
  read_at?: string | null;
  created_at: string;
}

export async function listNotifications(params: { is_read?: boolean; page?: number } = {}) {
  const { data } = await api.get<Paginated<NotificationRecord>>("/notifications/", {
    params: { ...params, page_size: 20 },
  });
  return data;
}

export async function unreadNotificationCount() {
  const { data } = await api.get<{ unread: number }>(
    "/notifications/unread-count/",
  );
  return data.unread;
}

export async function markNotificationRead(id: string) {
  const { data } = await api.post<NotificationRecord>(
    `/notifications/${id}/mark-read/`,
  );
  return data;
}

export async function markAllNotificationsRead() {
  const { data } = await api.post<{ marked_read: number }>(
    "/notifications/mark-all-read/",
  );
  return data;
}
