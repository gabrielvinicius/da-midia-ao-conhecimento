import * as React from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';

import { Button } from '../../../components/ui/Button';
import { Input } from '../../../components/ui/Input';
import { Label } from '../../../components/ui/Label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../../../components/ui/Select"; // I will create this component next
import { useUploadMedia } from '../hooks/useMedia';

const MAX_FILE_SIZE = 500 * 1024 * 1024; // 500 MB
const ACCEPTED_FILE_TYPES = ["video/mp4", "video/webm", "video/quicktime", "audio/mpeg", "audio/wav"];

const uploadSchema = z.object({
  storageProvider: z.string(),
  file: z
    .any()
    .refine((files) => files?.length == 1, "File is required.")
    .refine((files) => files?.[0]?.size <= MAX_FILE_SIZE, `Max file size is 500MB.`)
    .refine(
      (files) => ACCEPTED_FILE_TYPES.includes(files?.[0]?.type),
      ".mp4, .webm, .mov, .mp3, .wav files are accepted."
    ),
});

type UploadFormValues = z.infer<typeof uploadSchema>;

export const UploadForm = () => {
  const { mutate: upload, isPending } = useUploadMedia();

  const form = useForm<UploadFormValues>({
    resolver: zodResolver(uploadSchema),
    defaultValues: {
      storageProvider: 'local',
    },
  });

  const onSubmit = (data: UploadFormValues) => {
    upload({ file: data.file[0], storageProvider: data.storageProvider });
  };

  return (
    <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
      <div className="space-y-2">
        <Label htmlFor="file">Media File</Label>
        <Input
          id="file"
          type="file"
          {...form.register('file')}
          disabled={isPending}
        />
        {form.formState.errors.file && (
          <p className="text-sm text-destructive">{form.formState.errors.file.message?.toString()}</p>
        )}
      </div>
      <div className="space-y-2">
        <Label htmlFor="storage-provider">Storage Provider</Label>
        <Select
          defaultValue="local"
          onValueChange={(value) => form.setValue('storageProvider', value)}
          disabled={isPending}
        >
          <SelectTrigger id="storage-provider">
            <SelectValue placeholder="Select a provider" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="local">Local</SelectItem>
            <SelectItem value="s3">Amazon S3</SelectItem>
          </SelectContent>
        </Select>
      </div>
      <Button type="submit" className="w-full" disabled={isPending}>
        {isPending ? 'Uploading...' : 'Upload Media'}
      </Button>
    </form>
  );
};
