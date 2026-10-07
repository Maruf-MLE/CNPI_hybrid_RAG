import { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Privacy Policy - CNPIchat',
  description: 'Privacy Policy for CNPIchat - RAG-powered Q&A chatbot for CNPI (Cumilla Polytechnic Institute)',
};

export default function PrivacyPolicy() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50">
      <div className="max-w-4xl mx-auto px-4 py-12 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold text-gray-900 mb-4">
            Privacy Policy
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
              1. Introduction
            </h2>
            <p className="text-gray-700 leading-relaxed">
              Welcome to CNPIchat. We are committed to protecting your privacy and ensuring the security 
              of your personal information. This Privacy Policy explains how we collect, use, and safeguard 
              your data when you use our RAG-powered Q&A chatbot service for Cumilla Polytechnic Institute 
              (CNPI).
            </p>
          </section>

          {/* Information We Collect */}
          <section>
            <h2 className="text-2xl font-semibold text-gray-900 mb-4">
              2. Information We Collect
            </h2>
            <div className="space-y-4">
              <div>
                <h3 className="text-lg font-medium text-gray-800 mb-2">
                  2.1 Information You Provide
                </h3>
                <ul className="list-disc list-inside text-gray-700 space-y-2 ml-4">
                  <li>Questions and messages you send to the chatbot</li>
                  <li>Feedback and ratings you provide</li>
                  <li>Any information included in your chat conversations</li>
                </ul>
              </div>

              <div>
                <h3 className="text-lg font-medium text-gray-800 mb-2">
                  2.2 Automatically Collected Information
                </h3>
                <ul className="list-disc list-inside text-gray-700 space-y-2 ml-4">
                  <li>Session IDs (temporary identifiers for your chat session)</li>
                  <li>Timestamps of your interactions</li>
                  <li>Device type and browser information</li>
                  <li>IP address (anonymized)</li>
                </ul>
              </div>

              <div>
                <h3 className="text-lg font-medium text-gray-800 mb-2">
                  2.3 Facebook Messenger Data (if using Messenger bot)
                </h3>
                <ul className="list-disc list-inside text-gray-700 space-y-2 ml-4">
                  <li>Page-Scoped User ID (PSID) - a unique identifier from Facebook</li>
                  <li>Messages you send to our Facebook Page</li>
                  <li>No access to your Facebook profile information, friends list, or other Facebook data</li>
                </ul>
              </div>
            </div>
          </section>

          {/* How We Use Your Information */}
          <section>
            <h2 className="text-2xl font-semibold text-gray-900 mb-4">
              3. How We Use Your Information
            </h2>
            <p className="text-gray-700 mb-3">We use your information to:</p>
            <ul className="list-disc list-inside text-gray-700 space-y-2 ml-4">
              <li>Provide accurate answers to your questions about CNPI</li>
              <li>Maintain conversation context for multi-turn interactions</li>
              <li>Improve our chatbot's performance and accuracy</li>
              <li>Analyze usage patterns to enhance user experience</li>
              <li>Detect and prevent abuse or misuse of the service</li>
              <li>Comply with legal obligations</li>
            </ul>
          </section>

          {/* Data Storage and Security */}
          <section>
            <h2 className="text-2xl font-semibold text-gray-900 mb-4">
              4. Data Storage and Security
            </h2>
            <div className="space-y-3 text-gray-700">
              <p>
                <strong className="text-gray-900">Storage:</strong> Your chat sessions are stored 
                in-memory for up to 1 hour of inactivity. After that, they are automatically deleted. 
                We do not permanently store your personal conversations unless explicitly saved for 
                quality improvement purposes (anonymized).
              </p>
              <p>
                <strong className="text-gray-900">Security:</strong> We implement industry-standard 
                security measures including:
              </p>
              <ul className="list-disc list-inside space-y-2 ml-4">
                <li>HTTPS encryption for all data transmission</li>
                <li>Secure database connections with SSL/TLS</li>
                <li>HMAC-SHA256 signature verification for Facebook Messenger webhooks</li>
                <li>Regular security audits and updates</li>
                <li>Access controls and authentication for administrative functions</li>
              </ul>
            </div>
          </section>

          {/* Data Sharing */}
          <section>
            <h2 className="text-2xl font-semibold text-gray-900 mb-4">
              5. Data Sharing and Third Parties
            </h2>
            <div className="space-y-3 text-gray-700">
              <p>We do <strong className="text-gray-900">NOT</strong> sell, rent, or trade your personal information.</p>
              <p>We may share data with:</p>
              <ul className="list-disc list-inside space-y-2 ml-4">
                <li>
                  <strong>Google Gemini AI:</strong> Questions are sent to Google's Gemini API to generate 
                  answers. Google's privacy policy applies: 
                  <a href="https://policies.google.com/privacy" className="text-blue-600 hover:underline ml-1" target="_blank" rel="noopener noreferrer">
                    https://policies.google.com/privacy
                  </a>
                </li>
                <li>
                  <strong>Hosting Provider (Render/Netlify):</strong> For infrastructure and deployment
                </li>
                <li>
                  <strong>Facebook/Meta:</strong> Only when you use our Messenger bot (subject to Meta's privacy policy)
                </li>
                <li>
                  <strong>Legal Requirements:</strong> If required by law or to protect our rights
                </li>
              </ul>
            </div>
          </section>

          {/* Your Rights */}
          <section>
            <h2 className="text-2xl font-semibold text-gray-900 mb-4">
              6. Your Rights
            </h2>
            <p className="text-gray-700 mb-3">You have the right to:</p>
            <ul className="list-disc list-inside text-gray-700 space-y-2 ml-4">
              <li>Access the data we have about you</li>
              <li>Request deletion of your chat history</li>
              <li>Opt-out of data collection (by not using the service)</li>
              <li>Withdraw consent at any time</li>
              <li>File a complaint with relevant data protection authorities</li>
            </ul>
            <p className="text-gray-700 mt-4">
              To exercise these rights, contact us at:{' '}
              <a href="mailto:hmaruf291@gmail.com" className="text-blue-600 hover:underline">
                hmaruf291@gmail.com
              </a>
            </p>
          </section>

          {/* Cookies */}
          <section>
            <h2 className="text-2xl font-semibold text-gray-900 mb-4">
              7. Cookies and Tracking
            </h2>
            <p className="text-gray-700">
              We use session cookies to maintain your chat session. These cookies are temporary and 
              are deleted when you close your browser. We do not use third-party tracking cookies or 
              analytics that identify you personally.
            </p>
          </section>

          {/* Children's Privacy */}
          <section>
            <h2 className="text-2xl font-semibold text-gray-900 mb-4">
              8. Children's Privacy
            </h2>
            <p className="text-gray-700">
              CNPIchat is intended for students, faculty, and staff of Cumilla Polytechnic Institute. 
              While we do not knowingly collect personal information from children under 13, our service 
              may be used by polytechnic students. We encourage parents and guardians to supervise their 
              children's online activities.
            </p>
          </section>

          {/* Data Retention */}
          <section>
            <h2 className="text-2xl font-semibold text-gray-900 mb-4">
              9. Data Retention
            </h2>
            <ul className="list-disc list-inside text-gray-700 space-y-2 ml-4">
              <li>
                <strong>Chat Sessions:</strong> Stored in-memory for 1 hour of inactivity, then automatically deleted
              </li>
              <li>
                <strong>Anonymized Analytics:</strong> Retained indefinitely for service improvement
              </li>
              <li>
                <strong>Messenger Messages:</strong> Message IDs stored for 30 days for duplicate prevention
              </li>
            </ul>
          </section>

          {/* Changes to Policy */}
          <section>
            <h2 className="text-2xl font-semibold text-gray-900 mb-4">
              10. Changes to This Privacy Policy
            </h2>
            <p className="text-gray-700">
              We may update this Privacy Policy from time to time. We will notify users of significant 
              changes by posting the new Privacy Policy on this page and updating the "Last updated" date. 
              Continued use of CNPIchat after changes constitutes acceptance of the updated policy.
            </p>
          </section>

          {/* Contact */}
          <section>
            <h2 className="text-2xl font-semibold text-gray-900 mb-4">
              11. Contact Us
            </h2>
            <div className="bg-blue-50 rounded-lg p-6 space-y-2">
              <p className="text-gray-700">
                If you have questions about this Privacy Policy or our data practices, please contact:
              </p>
              <div className="text-gray-800 space-y-1">
                <p><strong>Email:</strong> hmaruf291@gmail.com</p>
                <p><strong>Organization:</strong> Cumilla Polytechnic Institute (CNPI)</p>
                <p><strong>Project:</strong> CNPIchat - Hybrid RAG Q&A System</p>
                <p><strong>Website:</strong> <a href="https://cnpichat.netlify.app" className="text-blue-600 hover:underline">https://cnpichat.netlify.app</a></p>
              </div>
            </div>
          </section>

          {/* Footer Note */}
          <section className="border-t pt-6 mt-8">
            <p className="text-sm text-gray-600 text-center">
              This Privacy Policy is compliant with Facebook Platform Policies and applicable data 
              protection regulations including GDPR principles.
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
