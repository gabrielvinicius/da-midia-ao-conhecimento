export type Video = {
    id: string;
    file_path: string;
    status: "UPLOADED" | "PROCESSING" | "COMPLETED" | "FAILED";
    created_at: string;
};

export type Transcription = {
    id: string;
    video_id: string;
    text: string;
    status: "PROCESSING" | "COMPLETED" | "FAILED";
    created_at: string;
};

export type Summary = {
    id: string;
    transcription_id: string;
    text: string;
    status: "PROCESSING" | "COMPLETED" | "FAILED";
    created_at: string;
};

export type User = {
    id: string;
    email: string;
    is_active: boolean;
    role: "user" | "admin";
};

export type Notification = {
    id: string;
    user_id: string;
    type: "EMAIL" | "SMS" | "WEBHOOK";
    content: string;
    status: "PENDING" | "SENT" | "FAILED";
    created_at: string;
};