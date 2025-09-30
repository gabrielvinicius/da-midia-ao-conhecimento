import * as React from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';

import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Label } from "@/components/ui/Label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/Select";
import { useUploadMedia } from '../hooks/useMedia';
import { useProviders } from '@/features/providers/hooks/useProviders';

const MAX_FILE_SIZE = 500 * 1024 * 1024; // 500 MB
const ACCEPTED_FILE_TYPES = ["video/mp4", "video/webm", "video/quicktime", "audio/mpeg", "audio/wav", "application/pdf", "text/plain"];

const uploadSchema = z.object({
  storageProvider: z.string(),
  transcriptionProvider: z.string().optional(),
  summarizationProvider: z.string().optional(),
  file: z
    .any()
    .refine((files) => files?.length == 1, "File is required.")
    .refine((files) => files?.[0]?.size <= MAX_FILE_SIZE, `Max file size is 500MB.`)
    .refine(
      (files) => ACCEPTED_FILE_TYPES.includes(files?.[0]?.type),
      ".mp4, .webm, .mov, .mp3, .wav, .pdf, .txt files are accepted."
    ),
});

type UploadFormValues = z.infer<typeof uploadSchema>;

export const UploadForm = () => {
  const { mutate: upload, isPending } = useUploadMedia();
  const { data: transcriptionProviders } = useProviders("transcription");
  const { data: summarizationProviders } = useProviders("summarization");

  const form = useForm<UploadFormValues>({
    resolver: zodResolver(uploadSchema),
    defaultValues: {
      storageProvider: 'local',
    },
  });

  const onSubmit = (data: UploadFormValues) => {
    upload({ 
      file: data.file[0], 
      storageProvider: data.storageProvider,
      transcriptionProvider: data.transcriptionProvider,
      summarizationProvider: data.summarizationProvider,
    });
  };

  return (
    <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
      <div className="space-y-2">
        <Label htmlFor="file">Media File</Label>
        <Input id="file" type="file" {...form.register('file')} disabled={isPending} />
        {form.formState.errors.file && (
          <p className="text-sm text-destructive">{form.formState.errors.file.message?.toString()}</p>
        )}
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label htmlFor="transcription-provider">Transcription Provider</Label>
          <Select onValueChange={(value) => form.setValue('transcriptionProvider', value)} disabled={isPending}>
            <SelectTrigger id="transcription-provider">
              <SelectValue placeholder="Select a provider (optional)" />
            </SelectTrigger>
            <SelectContent>
              {transcriptionProviders?.map(p => <SelectItem key={p} value={p}>{p}</SelectItem>)}
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-2">
          <Label htmlFor="summarization-provider">Summarization Provider</Label>
          <Select onValueChange={(value) => form.setValue('summarizationProvider', value)} disabled={isPending}>
            <SelectTrigger id="summarization-provider">
              <SelectValue placeholder="Select a provider (optional)" />
            </SelectTrigger>
            <SelectContent>
              {summarizationProviders?.map(p => <SelectItem key={p} value={p}>{p}</SelectItem>)}
            </SelectContent>
          </Select>
        </div>
      </div>

      <Button type="submit" className="w-full" disabled={isPending}>
        {isPending ? 'Uploading...' : 'Upload Media'}
      </Button>
    </form>
  );
};
