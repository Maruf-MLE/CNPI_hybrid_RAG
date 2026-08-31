import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import {
  structuredData,
  organizationStructuredData,
  faqStructuredData,
} from "../lib/structured-data";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  metadataBase: new URL('https://cnpichat.netlify.app'),
  title: {
    default: 'CNPI RAG - AI-Powered College Information System',
    template: '%s | CNPI RAG'
  },
  description: 'CNPI RAG is an advanced AI-powered chatbot system for Cumilla Polytechnic Institute (CNPI) providing instant answers about classes, routines, teachers, departments, labs, and college information using Retrieval-Augmented Generation (RAG) technology.',
  keywords: [
    'CNPI',
    'Cumilla Polytechnic Institute',
    'AI Chatbot',
    'RAG System',
    'College Information',
    'Class Routine',
    'Teachers Information',
    'Lab Information',
    'Department Information',
    'Student Portal',
    'Bangladesh Polytechnic',
    'Technical Education',
    'CST Department',
    'Computer Science',
    'Engineering'
  ],
  authors: [{ name: 'CNPI Development Team' }],
  creator: 'CNPI Development Team',
  publisher: 'Cumilla Polytechnic Institute',
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      'max-video-preview': -1,
      'max-image-preview': 'large',
      'max-snippet': -1,
    },
  },
  openGraph: {
    type: 'website',
    locale: 'en_US',
    alternateLocale: ['bn_BD'],
    url: 'https://cnpichat.netlify.app',
    title: 'CNPI RAG - AI-Powered College Information System',
    description: 'Get instant answers about CNPI classes, routines, teachers, labs, and departments using our advanced AI chatbot powered by RAG technology.',
    siteName: 'CNPI RAG',
    images: [
      {
        url: '/api/og?title=CNPI+RAG&subtitle=AI-Powered+College+Information+System',
        width: 1200,
        height: 630,
        alt: 'CNPI RAG - AI Chatbot System',
      },
    ],
  },
  twitter: {
    card: 'summary_large_image',
    title: 'CNPI RAG - AI-Powered College Information System',
    description: 'Get instant answers about CNPI using our AI chatbot',
    images: ['/api/og?title=CNPI+RAG&subtitle=AI-Powered+College+Information+System'],
  },
  verification: {
    google: 'google26a045fcefe124ca', // Google Search Console verification
  },
  alternates: {
    canonical: 'https://cnpichat.netlify.app',
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
      suppressHydrationWarning
    >
      <head>
        <link rel="icon" href="/favicon.ico" sizes="any" />
        <link rel="apple-touch-icon" href="/apple-touch-icon.png" />
        <meta name="theme-color" content="#0f172a" />
        {/* JSON-LD Structured Data for rich search results */}
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(structuredData) }}
        />
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(organizationStructuredData) }}
        />
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(faqStructuredData) }}
        />
      </head>
      <body className="min-h-full flex flex-col" suppressHydrationWarning>
        {children}
      </body>
    </html>
  );
}
