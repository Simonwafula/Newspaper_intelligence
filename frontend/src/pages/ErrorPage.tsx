import { Link } from 'react-router-dom';
import { PageContainer } from '../components/layout';
import { Button } from '../components/ui';

const ErrorPage = () => {
  return (
    <PageContainer maxWidth="lg">
      <div className="flex flex-col items-center justify-center py-20 text-center">
        <div className="text-8xl font-serif font-bold text-stone-300 mb-4">404</div>
        <h1 className="text-2xl font-bold text-ink-800 mb-2">Page Not Found</h1>
        <p className="text-stone-600 mb-8">
          The page you're looking for doesn't exist or has been moved.
        </p>
        <Link to="/">
          <Button>Go to Home</Button>
        </Link>
      </div>
    </PageContainer>
  );
};

export default ErrorPage;
