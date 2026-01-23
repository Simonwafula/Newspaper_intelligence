import { ItemWithStructuredData, TenderStructuredData } from '../types';

interface TenderCardProps {
  item: ItemWithStructuredData;
  onClick?: () => void;
}

export function TenderCard({ item, onClick }: TenderCardProps) {
  const data = item.structured_data as TenderStructuredData | undefined;
  const contact = item.contact_info_json;

  const formatValue = () => {
    if (!data?.estimated_value) return null;
    const currency = data.currency || 'USD';
    return `${currency} ${data.estimated_value.toLocaleString()}`;
  };

  const isDeadlineSoon = () => {
    if (!data?.deadline) return false;
    // Simple check - if deadline contains urgent keywords
    const deadlineText = data.deadline.toLowerCase();
    return deadlineText.includes('urgent') || deadlineText.includes('immediate');
  };

  return (
    <div
      className={`bg-white border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow ${onClick ? 'cursor-pointer' : ''}`}
      onClick={onClick}
    >
      {/* Header */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-1">
            <span className="px-2 py-0.5 bg-purple-100 text-purple-800 text-xs font-medium rounded">
              TENDER
            </span>
            {data?.tender_reference && (
              <span className="px-2 py-0.5 bg-gray-100 text-gray-700 text-xs font-mono rounded">
                {data.tender_reference}
              </span>
            )}
            {isDeadlineSoon() && (
              <span className="px-2 py-0.5 bg-red-100 text-red-800 text-xs font-medium rounded">
                URGENT
              </span>
            )}
          </div>
          <h3 className="font-semibold text-gray-900 text-lg">
            {data?.title || item.title || 'Tender Notice'}
          </h3>
          {data?.issuer && (
            <p className="text-gray-600 text-sm mt-0.5">
              <span className="font-medium">Issued by:</span> {data.issuer}
            </p>
          )}
        </div>
      </div>

      {/* Key Details Grid */}
      <div className="grid grid-cols-2 gap-3 mb-3">
        {formatValue() && (
          <div className="flex items-center gap-2">
            <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <div>
              <span className="text-xs text-gray-500 block">Estimated Value</span>
              <span className="text-sm font-medium text-gray-900">{formatValue()}</span>
            </div>
          </div>
        )}
        {data?.deadline && (
          <div className="flex items-center gap-2">
            <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <div>
              <span className="text-xs text-gray-500 block">Deadline</span>
              <span className={`text-sm font-medium ${isDeadlineSoon() ? 'text-red-600' : 'text-gray-900'}`}>
                {data.deadline}
              </span>
            </div>
          </div>
        )}
      </div>

      {/* Categories */}
      {data?.category && data.category.length > 0 && (
        <div className="mb-3">
          <p className="text-xs text-gray-500 mb-1">Categories:</p>
          <div className="flex flex-wrap gap-1">
            {data.category.slice(0, 4).map((cat, i) => (
              <span key={i} className="px-2 py-0.5 bg-purple-50 text-purple-700 text-xs rounded">
                {cat}
              </span>
            ))}
            {data.category.length > 4 && (
              <span className="px-2 py-0.5 bg-gray-100 text-gray-500 text-xs rounded">
                +{data.category.length - 4} more
              </span>
            )}
          </div>
        </div>
      )}

      {/* Eligibility */}
      {data?.eligibility && data.eligibility.length > 0 && (
        <div className="mb-3">
          <p className="text-xs text-gray-500 mb-1">Eligibility Requirements:</p>
          <ul className="text-sm text-gray-700 list-disc list-inside space-y-0.5">
            {data.eligibility.slice(0, 3).map((req, i) => (
              <li key={i} className="line-clamp-1">{req}</li>
            ))}
            {data.eligibility.length > 3 && (
              <li className="text-gray-500">+{data.eligibility.length - 3} more requirements</li>
            )}
          </ul>
        </div>
      )}

      {/* Contact Info */}
      {data?.contact && data.contact.length > 0 && (
        <div className="border-t pt-3 mt-3">
          <p className="text-xs text-gray-500 mb-1">Contact:</p>
          <div className="flex flex-wrap gap-2">
            {data.contact.slice(0, 2).map((c, i) => (
              <span key={i} className="text-sm text-gray-700">{c}</span>
            ))}
          </div>
        </div>
      )}

      {/* Fallback Contact from parsed data */}
      {!data?.contact?.length && contact && (contact.email_addresses?.length || contact.phone_numbers?.length) && (
        <div className="border-t pt-3 mt-3">
          <p className="text-xs text-gray-500 mb-1">Contact:</p>
          <div className="flex flex-wrap gap-3">
            {contact.email_addresses?.slice(0, 1).map((email, i) => (
              <a
                key={i}
                href={`mailto:${email}`}
                className="text-sm text-blue-600 hover:underline"
                onClick={(e) => e.stopPropagation()}
              >
                {email}
              </a>
            ))}
            {contact.phone_numbers?.slice(0, 1).map((phone, i) => (
              <span key={i} className="text-sm text-gray-700">{phone}</span>
            ))}
          </div>
        </div>
      )}

      {/* Text Preview */}
      {item.text && !data?.title && (
        <p className="text-sm text-gray-600 line-clamp-3 mt-2">
          {item.text.slice(0, 200)}...
        </p>
      )}

      {/* Footer */}
      <div className="flex items-center justify-between mt-3 pt-3 border-t text-xs text-gray-500">
        <span>Page {item.page_number}</span>
        <span>{new Date(item.created_at).toLocaleDateString()}</span>
      </div>
    </div>
  );
}

export default TenderCard;
