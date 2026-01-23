import { ItemWithStructuredData, JobStructuredData } from '../types';

interface JobCardProps {
  item: ItemWithStructuredData;
  onClick?: () => void;
}

export function JobCard({ item, onClick }: JobCardProps) {
  const data = item.structured_data as JobStructuredData | undefined;
  const contact = item.contact_info_json;

  const formatSalary = () => {
    if (!data) return null;
    if (data.salary_description) return data.salary_description;
    if (data.salary_min && data.salary_max) {
      const currency = data.salary_currency || 'KES';
      return `${currency} ${data.salary_min.toLocaleString()} - ${data.salary_max.toLocaleString()}`;
    }
    if (data.salary_min) {
      const currency = data.salary_currency || 'KES';
      return `${currency} ${data.salary_min.toLocaleString()}+`;
    }
    return null;
  };

  const formatExperience = () => {
    if (!data) return null;
    if (data.experience_years_min && data.experience_years_max) {
      return `${data.experience_years_min}-${data.experience_years_max} years`;
    }
    if (data.experience_years || data.experience_years_min) {
      return `${data.experience_years || data.experience_years_min}+ years`;
    }
    return null;
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
            <span className="px-2 py-0.5 bg-blue-100 text-blue-800 text-xs font-medium rounded">
              JOB
            </span>
            {data?.work_mode && (
              <span className="px-2 py-0.5 bg-green-100 text-green-800 text-xs font-medium rounded">
                {data.work_mode}
              </span>
            )}
          </div>
          <h3 className="font-semibold text-gray-900 text-lg">
            {data?.job_title || item.title || 'Job Listing'}
          </h3>
          {data?.employer && (
            <p className="text-gray-600 text-sm mt-0.5">{data.employer}</p>
          )}
        </div>
      </div>

      {/* Key Details Grid */}
      <div className="grid grid-cols-2 gap-3 mb-3">
        {formatSalary() && (
          <div className="flex items-center gap-2">
            <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span className="text-sm text-gray-700">{formatSalary()}</span>
          </div>
        )}
        {formatExperience() && (
          <div className="flex items-center gap-2">
            <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 13.255A23.931 23.931 0 0112 15c-3.183 0-6.22-.62-9-1.745M16 6V4a2 2 0 00-2-2h-4a2 2 0 00-2 2v2m4 6h.01M5 20h14a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
            </svg>
            <span className="text-sm text-gray-700">{formatExperience()}</span>
          </div>
        )}
        {data?.work_location && (
          <div className="flex items-center gap-2">
            <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
            <span className="text-sm text-gray-700">{data.work_location}</span>
          </div>
        )}
        {data?.application_deadline && (
          <div className="flex items-center gap-2">
            <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
            </svg>
            <span className="text-sm text-gray-700">Deadline: {data.application_deadline}</span>
          </div>
        )}
      </div>

      {/* Sectors */}
      {data?.sector && data.sector.length > 0 && (
        <div className="flex flex-wrap gap-1 mb-3">
          {data.sector.slice(0, 3).map((s, i) => (
            <span key={i} className="px-2 py-0.5 bg-gray-100 text-gray-700 text-xs rounded">
              {s}
            </span>
          ))}
          {data.sector.length > 3 && (
            <span className="px-2 py-0.5 bg-gray-100 text-gray-500 text-xs rounded">
              +{data.sector.length - 3} more
            </span>
          )}
        </div>
      )}

      {/* Qualifications Preview */}
      {data?.qualifications && data.qualifications.length > 0 && (
        <div className="mb-3">
          <p className="text-xs text-gray-500 mb-1">Qualifications:</p>
          <p className="text-sm text-gray-700 line-clamp-2">
            {data.qualifications.slice(0, 3).join(', ')}
            {data.qualifications.length > 3 && ` +${data.qualifications.length - 3} more`}
          </p>
        </div>
      )}

      {/* Education */}
      {data?.education_requirements && data.education_requirements.length > 0 && (
        <div className="mb-3">
          <p className="text-xs text-gray-500 mb-1">Education:</p>
          <p className="text-sm text-gray-700">
            {data.education_requirements[0]}
          </p>
        </div>
      )}

      {/* Contact Info */}
      {contact && (contact.email_addresses?.length || contact.phone_numbers?.length) && (
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
      {item.text && !data?.job_title && (
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

export default JobCard;
