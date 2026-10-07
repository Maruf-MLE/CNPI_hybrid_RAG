import { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Terms of Service - CNPIchat',
  description: 'Terms of Service for CNPIchat - RAG-powered Q&A chatbot for CNPI (Cumilla Polytechnic Institute)',
};

export default function TermsOfService() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50">
      <div className="max-w-4xl mx-auto px-4 py-12 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold text-gray-900 mb-4">
            Terms of Service
          </h1>
          <p className="text-gray-600">
            Last updated: October 7, 2026
          </p>
        </div>

        {/* Content */}
        <div className="bg-white rounded-2xl shadow-lg p-8 space-y-8">
          {/* Introduction */}
          <section>
            <h2 className="text-2xl font-semibold text-gray-900 mb-4">
              1. Acceptance of Terms
            </h2>
            <p className="text-gray-700 leading-relaxed">
              By accessing and using CNPIchat ("the Service"), you accept and agree to be bound by these 
              Terms of Service ("Terms"). If you do not agree to these Terms, please do not use the Service. 
              CNPIchat is a RAG-powered (Retrieval-Augmented Generation) Q&A chatbot designed to provide 
              information about Cumilla Polytechnic Institute (CNPI).
            </p>
          </section>

          {/* Service Description */}
          <section>
            <h2 className="text-2xl font-semibold text-gray-900 mb-4">
              2. Service Description
            </h2>
            <div className="space-y-3 text-gray-700">
              <p>CNPIchat provides:</p>
              <ul className="list-disc list-inside space-y-2 ml-4">
                <li>AI-powered answers to questions about CNPI (departments, faculty, courses, facilities, etc.)</li>
                <li>Web-based chat interface at cnpichat.netlify.app</li>
                <li>Facebook Messenger bot integration</li>
                <li>Multi-turn conversation support with context retention</li>
              </ul>
              <p className="mt-4">
                The Service is provided free of charge for educational purposes.
              </p>
            </div>
          </section>

          {/* Eligibility */}
          <section>
            <h2 className="text-2xl font-semibold text-gray-900 mb-4">
              3. Eligibility
            </h2>
            <p className="text-gray-700">
              The Service is intended for students, faculty, staff, and prospective students of Cumilla 
              Polytechnic Institute. By using the Service, you represent that you are at least 13 years old. 
              Users under 18 should have parental consent.
            </p>
          </section>

          {/* Acceptable Use */}
          <section>
            <h2 className="text-2xl font-semibold text-gray-900 mb-4">
              4. Acceptable Use Policy
            </h2>
            <div className="space-y-3 text-gray-700">
              <p>You agree to use CNPIchat only for lawful purposes. You must NOT:</p>
              <ul className="list-disc list-inside space-y-2 ml-4">
                <li>Submit harmful, offensive, abusive, or inappropriate content</li>
                <li>Attempt to exploit, hack, or disrupt the Service</li>
                <li>Use automated tools (bots, scripts) to spam or overload the Service</li>
                <li>Impersonate any person or entity</li>
                <li>Violate any applicable laws or regulations</li>
                <li>Use the Service to distribute malware or viruses</li>
                <li>Attempt to reverse-engineer or extract the AI model</li>
                <li>Collect or harvest personal information of other users</li>
              </ul>
            </div>
          </section>

          {/* Intellectual Property */}
          <section>
            <h2 className="text-2xl font-semibold text-gray-900 mb-4">
              5. Intellectual Property
            </h2>
            <div className="space-y-3 text-gray-700">
              <p>
                <strong className="text-gray-900">Service Ownership:</strong> CNPIchat, including its code, 
                design, and AI models, is owned by the project team. All rights reserved.
              </p>
              <p>
                <strong className="text-gray-900">Content Ownership:</strong> Information about CNPI 
                (departments, faculty, courses) is owned by Cumilla Polytechnic Institute.
              </p>
              <p>
                <strong className="text-gray-900">Your Content:</strong> You retain ownership of questions 
                and messages you submit. By using the Service, you grant us a license to process, store, 
                and use your messages to provide and improve the Service.
              </p>
            </div>
          </section>

          {/* AI-Generated Content */}
          <section>
            <h2 className="text-2xl font-semibold text-gray-900 mb-4">
              6. AI-Generated Content and Disclaimers
            </h2>
            <div className="bg-yellow-50 border-l-4 border-yellow-400 p-6 space-y-3">
              <p className="text-gray-800">
                <strong className="text-gray-900">⚠️ Important:</strong> CNPIchat uses AI (Google Gemini) 
                to generate answers. While we strive for accuracy:
              </p>
              <ul className="list-disc list-inside text-gray-700 space-y-2 ml-4">
                <li>Answers may contain errors, inaccuracies, or outdated information</li>
                <li>AI may occasionally "hallucinate" or provide incorrect responses</li>
                <li>Critical information (exam dates, admission requirements, fees) should be verified with official CNPI sources</li>
                <li>The Service is for informational purposes only and should not be considered official advice</li>
              </ul>
              <p className="text-gray-800 mt-4">
                <strong>Always verify important information with CNPI administration.</strong>
              </p>
            </div>
          </section>

          {/* Service Availability */}
          <section>
            <h2 className="text-2xl font-semibold text-gray-900 mb-4">
              7. Service Availability
            </h2>
            <p className="text-gray-700">
              We strive to keep CNPIchat available 24/7, but we do not guarantee uninterrupted access. 
              The Service may be temporarily unavailable due to maintenance, updates, or technical issues. 
              We reserve the right to modify, suspend, or discontinue the Service at any time without notice.
            </p>
          </section>

          {/* Limitation of Liability */}
          <section>
            <h2 className="text-2xl font-semibold text-gray-900 mb-4">
              8. Limitation of Liability
            </h2>
            <div className="space-y-3 text-gray-700">
              <p>
                <strong className="text-gray-900 uppercase">The Service is provided "as is" without warranties of any kind.</strong>
              </p>
              <p>To the fullest extent permitted by law:</p>
              <ul className="list-disc list-inside space-y-2 ml-4">
                <li>We are not liable for any damages arising from use of the Service</li>
                <li>We are not responsible for incorrect, incomplete, or outdated information</li>
                <li>We are not liable for decisions made based on AI-generated answers</li>
                <li>We are not responsible for third-party content or services (Google Gemini, Facebook, etc.)</li>
                <li>We are not liable for data loss, service interruptions, or security breaches</li>
              </ul>
              <p className="mt-4">
                Your use of the Service is at your own risk.
              </p>
            </div>
          </section>

          {/* Privacy */}
          <section>
            <h2 className="text-2xl font-semibold text-gray-900 mb-4">
              9. Privacy
            </h2>
            <p className="text-gray-700">
              Your use of CNPIchat is also governed by our{' '}
              <a href="/privacy" className="text-blue-600 hover:underline font-medium">
                Privacy Policy
              </a>
              . Please review it to understand how we collect, use, and protect your data.
            </p>
          </section>

          {/* Third-Party Services */}
          <section>
            <h2 className="text-2xl font-semibold text-gray-900 mb-4">
              10. Third-Party Services
            </h2>
            <div className="space-y-3 text-gray-700">
              <p>CNPIchat integrates with third-party services:</p>
              <ul className="list-disc list-inside space-y-2 ml-4">
                <li>
                  <strong>Google Gemini AI:</strong> For answer generation (
                  <a href="https://ai.google.dev/terms" className="text-blue-600 hover:underline" target="_blank" rel="noopener noreferrer">
                    Terms
                  </a>)
                </li>
                <li>
                  <strong>Facebook Messenger:</strong> For bot integration (
                  <a href="https://www.facebook.com/legal/terms" className="text-blue-600 hover:underline" target="_blank" rel="noopener noreferrer">
                    Terms
                  </a>)
                </li>
                <li>
                  <strong>Netlify/Render:</strong> For hosting
                </li>
              </ul>
              <p className="mt-4">
                Your use of these services is subject to their respective terms and policies. We are not 
                responsible for third-party actions or policies.
              </p>
            </div>
          </section>

          {/* Termination */}
          <section>
            <h2 className="text-2xl font-semibold text-gray-900 mb-4">
              11. Termination
            </h2>
            <p className="text-gray-700">
              We reserve the right to suspend or terminate your access to CNPIchat at any time, without 
              notice, for violating these Terms or for any other reason. You may stop using the Service 
              at any time. Upon termination, your chat session data will be deleted.
            </p>
          </section>

          {/* Changes to Terms */}
          <section>
            <h2 className="text-2xl font-semibold text-gray-900 mb-4">
              12. Changes to These Terms
            </h2>
            <p className="text-gray-700">
              We may update these Terms from time to time. We will notify users of significant changes by 
              posting the new Terms on this page and updating the "Last updated" date. Continued use of 
              the Service after changes constitutes acceptance of the updated Terms.
            </p>
          </section>

          {/* Governing Law */}
          <section>
            <h2 className="text-2xl font-semibold text-gray-900 mb-4">
              13. Governing Law
            </h2>
            <p className="text-gray-700">
              These Terms are governed by the laws of the People's Republic of Bangladesh. Any disputes 
              arising from these Terms or use of the Service shall be resolved in the courts of Cumilla, Bangladesh.
            </p>
          </section>

          {/* Contact */}
          <section>
            <h2 className="text-2xl font-semibold text-gray-900 mb-4">
              14. Contact Information
            </h2>
            <div className="bg-blue-50 rounded-lg p-6 space-y-2">
              <p className="text-gray-700">
                For questions about these Terms of Service, please contact:
              </p>
              <div className="text-gray-800 space-y-1">
                <p><strong>Email:</strong> hmaruf291@gmail.com</p>
                <p><strong>Organization:</strong> Cumilla Polytechnic Institute (CNPI)</p>
                <p><strong>Project:</strong> CNPIchat - Hybrid RAG Q&A System</p>
                <p><strong>Website:</strong> <a href="https://cnpichat.netlify.app" className="text-blue-600 hover:underline">https://cnpichat.netlify.app</a></p>
              </div>
            </div>
          </section>

          {/* Acknowledgment */}
          <section className="border-t pt-6 mt-8">
            <p className="text-sm text-gray-600">
              By using CNPIchat, you acknowledge that you have read, understood, and agree to be bound by 
              these Terms of Service and our Privacy Policy.
            </p>
          </section>
        </div>

        {/* Back to Home */}
        <div className="text-center mt-8">
          <a
            href="/"
            className="inline-flex items-center text-blue-600 hover:text-blue-700 font-medium"
          >
            ← Back to CNPIchat
          </a>
        </div>
      </div>
    </div>
  );
}
