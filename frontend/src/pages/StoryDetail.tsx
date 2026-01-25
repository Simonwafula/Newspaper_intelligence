import { useQuery } from '@tanstack/react-query';
import { Link, useParams } from 'react-router-dom';
import { itemsApi } from '../services/api';
import { PageContainer } from '../components/layout';
import { Card, Loading } from '../components/ui';

const StoryDetail = () => {
  const { editionId, groupId } = useParams<{ editionId: string; groupId: string }>();
  const editionIdNum = Number(editionId);
  const groupIdNum = Number(groupId);

  const { data: story, isLoading, error } = useQuery({
    queryKey: ['story-group', editionIdNum, groupIdNum],
    queryFn: () => itemsApi.getStoryGroup(editionIdNum, groupIdNum),
    enabled: Number.isFinite(editionIdNum) && Number.isFinite(groupIdNum),
  });

  if (isLoading) {
    return (
      <PageContainer>
        <Loading message="Loading story..." />
      </PageContainer>
    );
  }

  if (error || !story) {
    return (
      <PageContainer>
        <div className="p-4 bg-red-50 border border-red-200 text-red-700 rounded-lg">
          Unable to load story.
        </div>
      </PageContainer>
    );
  }

  return (
    <PageContainer>
      <div className="mb-4">
        <Link to={`/app/editions/${editionIdNum}`} className="text-ink-700 hover:text-ink-800 text-sm">
          &larr; Back to Edition
        </Link>
      </div>

      <Card className="p-6">
        <div className="mb-3 flex flex-wrap items-center gap-3 text-sm text-stone-500">
          <span>Story</span>
          {story.pages.length > 0 && <span>Pages {story.pages.join(', ')}</span>}
        </div>
        <h1 className="text-2xl font-bold text-ink-800 mb-4">
          {story.title || 'Untitled Story'}
        </h1>
        {story.full_text ? (
          <div className="prose prose-stone max-w-none">
            {story.full_text.split('\n').map((line, index) => (
              <p key={`${index}-${line.slice(0, 10)}`}>{line}</p>
            ))}
          </div>
        ) : (
          <p className="text-stone-500">No story text available.</p>
        )}
      </Card>
    </PageContainer>
  );
};

export default StoryDetail;
