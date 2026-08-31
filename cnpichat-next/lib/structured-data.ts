// SEO Structured Data for CNPI RAG
export const structuredData = {
  '@context': 'https://schema.org',
  '@type': 'WebApplication',
  name: 'CNPI RAG - AI-Powered College Information System',
  applicationCategory: 'EducationalApplication',
  operatingSystem: 'Web Browser',
  description: 'AI-powered chatbot system for Cumilla Polytechnic Institute providing instant answers about classes, routines, teachers, departments, and college information using RAG technology.',
  url: 'https://cnpichat.netlify.app',
  author: {
    '@type': 'Organization',
    name: 'CNPI Development Team',
  },
  publisher: {
    '@type': 'EducationalOrganization',
    name: 'Cumilla Polytechnic Institute',
    address: {
      '@type': 'PostalAddress',
      addressLocality: 'Cumilla',
      addressCountry: 'BD',
    },
  },
  offers: {
    '@type': 'Offer',
    price: '0',
    priceCurrency: 'BDT',
  },
  featureList: [
    'AI-Powered Chatbot',
    'Class Routine Information',
    'Teacher Directory',
    'Lab Information',
    'Department Details',
    'Real-time Answers',
    'Bengali Language Support',
    'RAG Technology',
  ],
};

export const organizationStructuredData = {
  '@context': 'https://schema.org',
  '@type': 'EducationalOrganization',
  name: 'Cumilla Polytechnic Institute',
  alternateName: 'CNPI',
  url: 'https://cnpichat.netlify.app',
  logo: 'https://cnpichat.netlify.app/logo.png',
  description: 'Leading polytechnic institute in Bangladesh offering technical education',
  address: {
    '@type': 'PostalAddress',
    addressLocality: 'Cumilla',
    addressRegion: 'Chittagong Division',
    addressCountry: 'BD',
  },
  contactPoint: {
    '@type': 'ContactPoint',
    contactType: 'customer support',
    availableLanguage: ['Bengali', 'English'],
  },
};

export const faqStructuredData = {
  '@context': 'https://schema.org',
  '@type': 'FAQPage',
  mainEntity: [
    {
      '@type': 'Question',
      name: 'What is CNPI RAG?',
      acceptedAnswer: {
        '@type': 'Answer',
        text: 'CNPI RAG is an AI-powered chatbot system for Cumilla Polytechnic Institute that provides instant answers about classes, routines, teachers, departments, labs, and college information using advanced Retrieval-Augmented Generation technology.',
      },
    },
    {
      '@type': 'Question',
      name: 'How do I use CNPI RAG chatbot?',
      acceptedAnswer: {
        '@type': 'Answer',
        text: 'Simply type your question in Bengali or English in the chat box. Ask about class routines, teacher information, lab details, department information, or any college-related query. The AI will provide instant, accurate answers.',
      },
    },
    {
      '@type': 'Question',
      name: 'What information can I get from CNPI RAG?',
      acceptedAnswer: {
        '@type': 'Answer',
        text: 'You can get information about class schedules, teacher profiles, lab facilities, department details, exam routines, college notices, admission information, and general college information.',
      },
    },
    {
      '@type': 'Question',
      name: 'Does CNPI RAG support Bengali language?',
      acceptedAnswer: {
        '@type': 'Answer',
        text: 'Yes, CNPI RAG fully supports Bengali (Bangla) language. You can ask questions in Bengali and receive answers in Bengali.',
      },
    },
    {
      '@type': 'Question',
      name: 'Is CNPI RAG free to use?',
      acceptedAnswer: {
        '@type': 'Answer',
        text: 'Yes, CNPI RAG is completely free for all students, teachers, and visitors of Cumilla Polytechnic Institute.',
      },
    },
  ],
};
