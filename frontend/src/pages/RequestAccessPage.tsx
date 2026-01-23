import { useState } from 'react';
import { Link } from 'react-router-dom';

interface RequestAccessFormData {
  full_name: string;
  email: string;
  organization: string;
  phone: string;
  reason: string;
  consent_not_redistribute: boolean;
  website_url: string; // Honeypot field
}

export default function RequestAccessPage() {
  const [formData, setFormData] = useState<RequestAccessFormData>({
    full_name: '',
    email: '',
    organization: '',
    phone: '',
    reason: '',
    consent_not_redistribute: false,
    website_url: '', // Honeypot field
  });
  const [error, setError] = useState<string>('');
  const [success, setSuccess] = useState<boolean>(false);
  const [loading, setLoading] = useState<boolean>(false);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value, type } = e.target;
    setFormData(prev => ({ 
      ...prev, 
      [name]: type === 'checkbox' ? (e.target as HTMLInputElement).checked : value 
    }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      const response = await fetch('/api/public/access-requests', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(formData),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to submit request');
      }

      setSuccess(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  if (success) {
    return (
      <div className="min-h-screen bg-stone-50 flex flex-col justify-center py-12 sm:px-6 lg:px-8">
        <div className="sm:mx-auto sm:w-full sm:max-w-md">
          <div className="text-center">
            <h1 className="font-serif text-3xl font-bold text-ink-800">
              Request Received
            </h1>
            <div className="mt-4 bg-green-50 border border-green-200 rounded-md p-4">
              <p className="text-sm text-green-800">
                Your access request has been received. You will be contacted if approved.
              </p>
            </div>
            <div className="mt-6">
              <Link
                to="/"
                className="font-medium text-ink-800 hover:text-ink-700"
              >
                Return to homepage
              </Link>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-stone-50 py-12 sm:px-6 lg:px-8">
      <div className="sm:mx-auto sm:w-full sm:max-w-md">
        <div className="text-center">
          <h1 className="font-serif text-3xl font-bold text-ink-800">
            Request Access
          </h1>
          <p className="mt-2 text-lg text-ink-600">
            Request access to Newspaper Intelligence
          </p>
        </div>

        <div className="mt-8 bg-white py-8 px-4 shadow sm:rounded-lg sm:px-10">
          <form className="space-y-6" onSubmit={handleSubmit}>
            {error && (
              <div className="bg-red-50 border border-red-200 rounded-md p-4">
                <p className="text-sm text-red-600">{error}</p>
              </div>
            )}

            <div>
              <label htmlFor="full_name" className="block text-sm font-medium text-ink-700">
                Full name *
              </label>
              <div className="mt-1">
                <input
                  id="full_name"
                  name="full_name"
                  type="text"
                  required
                  value={formData.full_name}
                  onChange={handleChange}
                  className="appearance-none block w-full px-3 py-2 border border-stone-300 rounded-md shadow-sm placeholder-stone-400 focus:outline-none focus:ring-ink-500 focus:border-ink-500 sm:text-sm"
                />
              </div>
            </div>

            <div>
              <label htmlFor="email" className="block text-sm font-medium text-ink-700">
                Email address *
              </label>
              <div className="mt-1">
                <input
                  id="email"
                  name="email"
                  type="email"
                  required
                  value={formData.email}
                  onChange={handleChange}
                  className="appearance-none block w-full px-3 py-2 border border-stone-300 rounded-md shadow-sm placeholder-stone-400 focus:outline-none focus:ring-ink-500 focus:border-ink-500 sm:text-sm"
                />
              </div>
            </div>

            <div>
              <label htmlFor="organization" className="block text-sm font-medium text-ink-700">
                Organization
              </label>
              <div className="mt-1">
                <input
                  id="organization"
                  name="organization"
                  type="text"
                  value={formData.organization}
                  onChange={handleChange}
                  className="appearance-none block w-full px-3 py-2 border border-stone-300 rounded-md shadow-sm placeholder-stone-400 focus:outline-none focus:ring-ink-500 focus:border-ink-500 sm:text-sm"
                />
              </div>
            </div>

            <div>
              <label htmlFor="phone" className="block text-sm font-medium text-ink-700">
                Phone number
              </label>
              <div className="mt-1">
                <input
                  id="phone"
                  name="phone"
                  type="tel"
                  value={formData.phone}
                  onChange={handleChange}
                  className="appearance-none block w-full px-3 py-2 border border-stone-300 rounded-md shadow-sm placeholder-stone-400 focus:outline-none focus:ring-ink-500 focus:border-ink-500 sm:text-sm"
                />
              </div>
            </div>

            <div>
              <label htmlFor="reason" className="block text-sm font-medium text-ink-700">
                Reason for access / intended use *
              </label>
              <div className="mt-1">
                <textarea
                  id="reason"
                  name="reason"
                  rows={4}
                  required
                  value={formData.reason}
                  onChange={handleChange}
                  placeholder="Please describe why you need access and how you plan to use the system..."
                  className="appearance-none block w-full px-3 py-2 border border-stone-300 rounded-md shadow-sm placeholder-stone-400 focus:outline-none focus:ring-ink-500 focus:border-ink-500 sm:text-sm"
                />
              </div>
            </div>

            {/* Honeypot field - hidden from users */}
            <input
              type="text"
              name="website_url"
              value={formData.website_url}
              onChange={handleChange}
              style={{ display: 'none' }}
              tabIndex={-1}
              autoComplete="off"
            />

            <div className="flex items-center">
              <input
                id="consent_not_redistribute"
                name="consent_not_redistribute"
                type="checkbox"
                required
                checked={formData.consent_not_redistribute}
                onChange={handleChange}
                className="h-4 w-4 text-ink-800 focus:ring-ink-500 border-stone-300 rounded"
              />
              <label htmlFor="consent_not_redistribute" className="ml-2 block text-sm text-ink-700">
                I agree not to redistribute or republish newspaper content. *
              </label>
            </div>

            <div>
              <button
                type="submit"
                disabled={loading}
                className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-ink-800 hover:bg-ink-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-ink-500 disabled:opacity-50"
              >
                {loading ? 'Submitting...' : 'Submit Request'}
              </button>
            </div>

            <div className="mt-6 text-center">
              <Link
                to="/"
                className="font-medium text-ink-800 hover:text-ink-700"
              >
                Back to homepage
              </Link>
              {' | '}
              <Link
                to="/login"
                className="font-medium text-ink-800 hover:text-ink-700"
              >
                Sign in
              </Link>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}