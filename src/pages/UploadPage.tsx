import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/Card";
import { UploadForm } from "../features/media/components/UploadForm";

const UploadPage = () => {
  return (
    <div className="flex items-center justify-center">
      <Card className="w-full max-w-2xl">
        <CardHeader>
          <CardTitle>Upload New Media</CardTitle>
          <CardDescription>
            Select a video or audio file and choose your storage provider.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <UploadForm />
        </CardContent>
      </Card>
    </div>
  );
};

export default UploadPage;
