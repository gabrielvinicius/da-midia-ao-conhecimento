import * as React from 'react';
import { useForm } from 'react-hook-form';

import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Label } from "@/components/ui/Label";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/Dialog";
import { useUpdateSpeakerAliases } from '../hooks/useTranscriptionMutations';
import { Transcription } from '@/types';

interface EditSpeakersDialogProps {
  transcription: Transcription;
}

export const EditSpeakersDialog = ({ transcription }: EditSpeakersDialogProps) => {
  const { mutate: updateAliases, isPending } = useUpdateSpeakerAliases();
  const [isOpen, setIsOpen] = React.useState(false);

  // Extract unique speaker IDs from the segments
  const uniqueSpeakers = React.useMemo(() => {
    const segments = transcription.result?.segments ?? [];
    if (!segments.length) return [];
    const speakers = new Set(segments.map(s => s.speaker).filter(Boolean));
    return Array.from(speakers) as string[];
  }, [transcription]);

  const { register, handleSubmit } = useForm<Record<string, string>>({
    defaultValues: transcription.speaker_aliases || {},
  });

  const onSubmit = (data: Record<string, string>) => {
    updateAliases({ transcriptionId: transcription.id, aliases: data }, {
      onSuccess: () => setIsOpen(false), // Close dialog on success
    });
  };

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <DialogTrigger asChild>
        <Button variant="outline" size="sm">Edit Speakers</Button>
      </DialogTrigger>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle>Edit Speaker Names</DialogTitle>
          <DialogDescription>
            Assign custom names to the identified speakers. Click save when you're done.
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4 py-4">
          {uniqueSpeakers.map(speakerId => (
            <div key={speakerId} className="grid grid-cols-4 items-center gap-4">
              <Label htmlFor={speakerId} className="text-right">
                {speakerId}
              </Label>
              <Input
                id={speakerId}
                {...register(speakerId)}
                className="col-span-3"
                placeholder="e.g., Alice, Bob..."
              />
            </div>
          ))}
          <DialogFooter>
            <Button type="submit" disabled={isPending}>
              {isPending ? 'Saving...' : 'Save Changes'}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
};
