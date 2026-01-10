import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { BookOpen, Shield, Users, Mail, Phone, MapPin, FileText, Upload, Search, Download, Settings, CheckCircle, AlertCircle, Info } from "lucide-react";
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from "@/components/ui/accordion";
import { Alert, AlertDescription } from "@/components/ui/alert";

const Support = () => {
  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl md:text-3xl font-bold bg-gradient-to-r from-primary to-accent bg-clip-text text-transparent">
          Support & Help Center
        </h1>
        <p className="text-muted-foreground mt-1">Everything you need to know about FinTrack</p>
      </div>

      {/* User Guide Section */}
      <div className="grid gap-4 md:gap-6 grid-cols-1 lg:grid-cols-2">
        <Card id="user-guide" className="shadow-soft border-border scroll-mt-6">
          <CardHeader className="border-b bg-gradient-to-r from-primary/5 to-accent/5">
            <div className="flex items-center gap-3">
              <div className="p-2.5 rounded-xl bg-primary/15">
                <BookOpen className="h-6 w-6 text-primary" />
              </div>
              <div>
                <CardTitle className="text-xl">User Guide</CardTitle>
                <p className="text-sm text-muted-foreground mt-1">Learn how to use FinTrack effectively</p>
              </div>
            </div>
          </CardHeader>
          <CardContent className="p-6">
            <Accordion type="single" collapsible className="w-full">
              <AccordionItem value="getting-started">
                <AccordionTrigger className="text-left font-semibold">
                  <div className="flex items-center gap-2">
                    <CheckCircle className="h-4 w-4 text-primary" />
                    Getting Started
                  </div>
                </AccordionTrigger>
                <AccordionContent className="space-y-3 text-sm text-muted-foreground">
                  <p>Welcome to FinTrack! Here's how to get started:</p>
                  <ol className="list-decimal list-inside space-y-2 ml-4">
                    <li><strong>Sign in:</strong> Use your credentials to access your dashboard.</li>
                    <li><strong>Set up integrations:</strong> Connect Gmail or other services in Settings to automate expense tracking.</li>
                    <li><strong>Upload documents:</strong> Use the Upload or Capture buttons to add invoices and receipts.</li>
                    <li><strong>Review and verify:</strong> Check imported data in the Transactions page before adding to your expenses.</li>
                  </ol>
                </AccordionContent>
              </AccordionItem>

              <AccordionItem value="uploading-documents">
                <AccordionTrigger className="text-left font-semibold">
                  <div className="flex items-center gap-2">
                    <Upload className="h-4 w-4 text-primary" />
                    Invoice Processing Workflow
                  </div>
                </AccordionTrigger>
                <AccordionContent className="space-y-4 text-sm text-muted-foreground">
                  <p className="font-medium text-foreground">FinTrack uses a 3-step workflow to process your invoices:</p>
                  
                  <div className="space-y-4 ml-4">
                    <div className="flex gap-3">
                      <div className="shrink-0 flex items-center justify-center w-8 h-8 rounded-full bg-primary/10 text-primary font-bold">1</div>
                      <div className="flex-1">
                        <h4 className="font-semibold text-foreground mb-1">Upload Invoice</h4>
                        <p>Upload your invoice using one of these methods:</p>
                        <ul className="list-disc list-inside space-y-1 ml-4 mt-2">
                          <li><strong>File Upload:</strong> Click "Upload Invoice" to select PDF, JPG, PNG, or WEBP files from your device.</li>
                          <li><strong>Folder Upload:</strong> Upload entire folders of documents at once for bulk processing.</li>
                          <li><strong>Camera Capture:</strong> Take a photo of physical receipts directly from the app.</li>
                        </ul>
                        <p className="mt-2 text-xs italic">Supported formats: PDF, JPEG, PNG, and WEBP files up to 10MB each.</p>
                      </div>
                    </div>

                    <div className="flex gap-3">
                      <div className="shrink-0 flex items-center justify-center w-8 h-8 rounded-full bg-accent/10 text-accent font-bold">2</div>
                      <div className="flex-1">
                        <h4 className="font-semibold text-foreground mb-1">AI Processing</h4>
                        <p>Once uploaded, our AI automatically extracts key information from your documents:</p>
                        <ul className="list-disc list-inside space-y-1 ml-4 mt-2">
                          <li>Invoice amount and currency</li>
                          <li>Vendor/merchant name</li>
                          <li>Date and invoice number</li>
                          <li>Category (automatically classified)</li>
                          <li>Payment method</li>
                          <li>Custom fields you've configured</li>
                        </ul>
                        <Alert className="bg-blue-50 dark:bg-blue-950/20 border-blue-200 dark:border-blue-900 mt-3">
                          <Info className="h-4 w-4 text-blue-600 dark:text-blue-400" />
                          <AlertDescription className="text-sm text-blue-800 dark:text-blue-300">
                            Processing happens in secure, isolated environments and typically completes within seconds.
                          </AlertDescription>
                        </Alert>
                      </div>
                    </div>

                    <div className="flex gap-3">
                      <div className="shrink-0 flex items-center justify-center w-8 h-8 rounded-full bg-green-100 dark:bg-green-900/30 text-green-600 dark:text-green-400 font-bold">3</div>
                      <div className="flex-1">
                        <h4 className="font-semibold text-foreground mb-1">Verify & Import</h4>
                        <p>After processing, your invoice appears in the <strong>Imported</strong> section of the All Transactions page:</p>
                        <ul className="list-disc list-inside space-y-1 ml-4 mt-2">
                          <li><strong>Review:</strong> Check the extracted information for accuracy.</li>
                          <li><strong>View Document:</strong> Click on any row or use the document icon to view the original file.</li>
                          <li><strong>Import:</strong> Once verified, click the "Import" button to add it to your <strong>My Expenses</strong>.</li>
                          <li><strong>Visibility:</strong> Only imported expenses appear in your dashboard analytics and reports.</li>
                        </ul>
                        <Alert className="bg-green-50 dark:bg-green-950/20 border-green-200 dark:border-green-900 mt-3">
                          <CheckCircle className="h-4 w-4 text-green-600 dark:text-green-400" />
                          <AlertDescription className="text-sm text-green-800 dark:text-green-300">
                            <strong>Important:</strong> Documents remain in the Imported section until you manually import them. This gives you full control to verify before adding to your expense records.
                          </AlertDescription>
                        </Alert>
                      </div>
                    </div>
                  </div>
                </AccordionContent>
              </AccordionItem>

              <AccordionItem value="managing-expenses">
                <AccordionTrigger className="text-left font-semibold">
                  <div className="flex items-center gap-2">
                    <FileText className="h-4 w-4 text-primary" />
                    Managing Expenses
                  </div>
                </AccordionTrigger>
                <AccordionContent className="space-y-3 text-sm text-muted-foreground">
                  <p>Organize and track your expenses efficiently:</p>
                  <ul className="space-y-2 ml-4">
                    <li><strong>Imported Section:</strong> View AI-processed documents that need review. Verify the extracted information and click "Import" to add them to your expenses.</li>
                    <li><strong>My Expenses:</strong> All confirmed expense records. You can edit, delete, or export these entries.</li>
                    <li><strong>Search & Filter:</strong> Use the search bar and category filters to quickly find specific transactions.</li>
                    <li><strong>Manual Entry:</strong> Click "Add Expense" to manually create an expense record without uploading a document.</li>
                    <li><strong>Custom Fields:</strong> Use the Schema button to add custom fields that match your business needs.</li>
                  </ul>
                </AccordionContent>
              </AccordionItem>

              <AccordionItem value="dashboard-analytics">
                <AccordionTrigger className="text-left font-semibold">
                  <div className="flex items-center gap-2">
                    <Search className="h-4 w-4 text-primary" />
                    Dashboard & Analytics
                  </div>
                </AccordionTrigger>
                <AccordionContent className="space-y-3 text-sm text-muted-foreground">
                  <p>Gain insights into your spending patterns:</p>
                  <ul className="space-y-2 ml-4">
                    <li><strong>Spending Overview:</strong> View total expenses, average transaction amount, and trends over time.</li>
                    <li><strong>Category Breakdown:</strong> See how much you're spending in each category with visual charts.</li>
                    <li><strong>Recent Transactions:</strong> Quick access to your latest expense entries.</li>
                    <li><strong>Time Filters:</strong> Analyze spending by different time periods (daily, weekly, monthly).</li>
                  </ul>
                </AccordionContent>
              </AccordionItem>

              <AccordionItem value="integrations">
                <AccordionTrigger className="text-left font-semibold">
                  <div className="flex items-center gap-2">
                    <Settings className="h-4 w-4 text-primary" />
                    Integrations
                  </div>
                </AccordionTrigger>
                <AccordionContent className="space-y-3 text-sm text-muted-foreground">
                  <p>Connect external services to automate expense tracking:</p>
                  <ul className="space-y-2 ml-4">
                    <li><strong>Gmail Integration:</strong> Automatically extract receipts and invoices from your email inbox.</li>
                    <li><strong>Auto-Sync:</strong> Integrated services sync periodically to import new documents.</li>
                    <li><strong>Credit Usage:</strong> Each integration feature consumes credits based on your plan.</li>
                    <li><strong>Manage Connections:</strong> Connect or disconnect integrations anytime from Settings.</li>
                  </ul>
                </AccordionContent>
              </AccordionItem>

              <AccordionItem value="exporting-data">
                <AccordionTrigger className="text-left font-semibold">
                  <div className="flex items-center gap-2">
                    <Download className="h-4 w-4 text-primary" />
                    Exporting Data
                  </div>
                </AccordionTrigger>
                <AccordionContent className="space-y-3 text-sm text-muted-foreground">
                  <p>Export your expense data for accounting or reporting:</p>
                  <ul className="space-y-2 ml-4">
                    <li><strong>CSV Export:</strong> Download your transactions in CSV format compatible with Excel and accounting software.</li>
                    <li><strong>Custom Fields:</strong> Exports include all custom fields you've configured.</li>
                    <li><strong>Filtered Exports:</strong> Apply filters before exporting to get specific subsets of data.</li>
                    <li><strong>Files Page:</strong> Access and download all uploaded documents from the Files page.</li>
                  </ul>
                </AccordionContent>
              </AccordionItem>
            </Accordion>
          </CardContent>
        </Card>
      </div>

      {/* Data & Compliance Section */}
      <div className="grid gap-4 md:gap-6 grid-cols-1 lg:grid-cols-2">
        <Card id="data-compliance" className="shadow-soft border-border scroll-mt-6">
          <CardHeader className="border-b bg-gradient-to-r from-accent/5 to-primary/5">
            <div className="flex items-center gap-3">
              <div className="p-2.5 rounded-xl bg-accent/15">
                <Shield className="h-6 w-6 text-accent" />
              </div>
              <div>
                <CardTitle className="text-xl">Data & Compliance</CardTitle>
                <p className="text-sm text-muted-foreground mt-1">How we protect and handle your data</p>
              </div>
            </div>
          </CardHeader>
          <CardContent className="p-6 space-y-6">
            <div className="space-y-4">
              <div className="space-y-3">
                <h3 className="font-semibold text-foreground flex items-center gap-2">
                  <Shield className="h-4 w-4 text-accent" />
                  Data Security
                </h3>
                <div className="text-sm text-muted-foreground space-y-2 ml-6">
                  <p><strong>Encryption:</strong> All data is encrypted in transit (TLS 1.3) and at rest (AES-256) to ensure maximum security.</p>
                  <p><strong>Secure Storage:</strong> Documents and data are stored on Amazon S3 with enterprise-grade security controls.</p>
                  <p><strong>Access Control:</strong> Only you can access your data. We implement strict authentication and authorization mechanisms.</p>
                  <p><strong>Regular Backups:</strong> Your data is automatically backed up to prevent loss.</p>
                </div>
              </div>

              <div className="space-y-3">
                <h3 className="font-semibold text-foreground flex items-center gap-2">
                  <AlertCircle className="h-4 w-4 text-accent" />
                  Privacy Policy
                </h3>
                <div className="text-sm text-muted-foreground space-y-2 ml-6">
                  <p><strong>Data Usage:</strong> We only use your data to provide and improve our services. We never sell your personal information.</p>
                  <p><strong>Third-Party Services:</strong> Integrations like Gmail access only the minimum data required (e.g., email attachments).</p>
                  <p><strong>Data Retention:</strong> You control your data. You can delete your account and all associated data at any time.</p>
                  <p><strong>Compliance:</strong> We adhere to GDPR, CCPA, and other applicable data protection regulations.</p>
                </div>
              </div>

              <div className="space-y-3">
                <h3 className="font-semibold text-foreground flex items-center gap-2">
                  <FileText className="h-4 w-4 text-accent" />
                  Document Processing
                </h3>
                <div className="text-sm text-muted-foreground space-y-2 ml-6">
                  <p><strong>AI Processing:</strong> We use advanced AI models to extract information from your documents. Processing happens in secure, isolated environments.</p>
                  <p><strong>Human Review:</strong> Your documents are never reviewed by humans unless you explicitly request support assistance.</p>
                  <p><strong>Data Accuracy:</strong> While we strive for accuracy, we recommend reviewing all AI-extracted data before importing to expenses.</p>
                  <p><strong>Duplicate Detection:</strong> Our system automatically detects duplicate uploads using cryptographic hashing to prevent redundant processing.</p>
                </div>
              </div>

              <Alert className="bg-green-50 dark:bg-green-950/20 border-green-200 dark:border-green-900">
                <CheckCircle className="h-4 w-4 text-green-600 dark:text-green-400" />
                <AlertDescription className="text-sm text-green-800 dark:text-green-300">
                  <strong>Your Control:</strong> You have full control over your data. Export, delete, or modify your information at any time through your account settings.
                </AlertDescription>
              </Alert>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* About Us Section */}
      <div className="grid gap-4 md:gap-6 grid-cols-1 lg:grid-cols-2">
        <Card id="about" className="shadow-soft border-border scroll-mt-6">
          <CardHeader className="border-b bg-gradient-to-r from-blue-50 to-purple-50 dark:from-blue-950/20 dark:to-purple-950/20">
            <div className="flex items-center gap-3">
              <div className="p-2.5 rounded-xl bg-blue-100 dark:bg-blue-900/30">
                <Users className="h-6 w-6 text-blue-600 dark:text-blue-400" />
              </div>
              <div>
                <CardTitle className="text-xl">About FinTrack</CardTitle>
                <p className="text-sm text-muted-foreground mt-1">Our mission and vision</p>
              </div>
            </div>
          </CardHeader>
          <CardContent className="p-6 space-y-5">
            <div className="space-y-3">
              <h3 className="font-semibold text-foreground">Our Mission</h3>
              <p className="text-sm text-muted-foreground leading-relaxed">
                FinTrack is built to simplify expense management for individuals and businesses. We believe that tracking expenses shouldn't be a tedious, time-consuming task. By leveraging cutting-edge AI and automation, we help you focus on what matters most while we handle the paperwork.
              </p>
            </div>

            <div className="space-y-3">
              <h3 className="font-semibold text-foreground">What We Offer</h3>
              <ul className="text-sm text-muted-foreground space-y-2 ml-4 list-disc">
                <li><strong>Automated Document Processing:</strong> Upload receipts and invoices, and let AI extract all the important details.</li>
                <li><strong>Smart Integrations:</strong> Connect your email and other services to automatically capture expense documents.</li>
                <li><strong>Customizable Tracking:</strong> Add custom fields and categories to match your unique business needs.</li>
                <li><strong>Powerful Analytics:</strong> Gain insights into spending patterns with intuitive dashboards and reports.</li>
                <li><strong>Secure & Compliant:</strong> Enterprise-grade security ensures your financial data is always protected.</li>
              </ul>
            </div>

            <div className="space-y-3">
              <h3 className="font-semibold text-foreground">Our Vision</h3>
              <p className="text-sm text-muted-foreground leading-relaxed">
                We envision a future where financial management is effortless and accessible to everyone. Whether you're a freelancer, small business owner, or finance professional, FinTrack adapts to your workflow and grows with you. We're continuously innovating to bring you the best expense management experience.
              </p>
            </div>

            <div className="pt-4 border-t">
              <p className="text-sm text-muted-foreground italic">
                Thank you for choosing FinTrack. We're committed to making your financial tracking simple, secure, and insightful.
              </p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Contact Section */}
      <div className="grid gap-4 md:gap-6 grid-cols-1 lg:grid-cols-2">
        <Card id="contact" className="shadow-soft border-border scroll-mt-6">
          <CardHeader className="border-b bg-gradient-to-r from-green-50 to-blue-50 dark:from-green-950/20 dark:to-blue-950/20">
            <div className="flex items-center gap-3">
              <div className="p-2.5 rounded-xl bg-green-100 dark:bg-green-900/30">
                <Mail className="h-6 w-6 text-green-600 dark:text-green-400" />
              </div>
              <div>
                <CardTitle className="text-xl">Contact Us</CardTitle>
                <p className="text-sm text-muted-foreground mt-1">We're here to help</p>
              </div>
            </div>
          </CardHeader>
          <CardContent className="p-6 space-y-6">
            <div className="flex items-center justify-center py-8 px-4">
              <div className="max-w-2xl text-center space-y-4">
                <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-gradient-to-r from-orange-100 to-green-100 dark:from-orange-900/30 dark:to-green-900/30">
                  <span className="text-2xl">🇮🇳</span>
                  <span className="font-semibold text-foreground">Proudly Made in India</span>
                </div>
                
                <div className="space-y-3">
                  <p className="text-muted-foreground text-sm">
                    FinTrack is currently in <strong className="text-foreground">active development</strong>. We're continuously improving and adding new features to make your expense tracking seamless.
                  </p>
                  
                  <Alert className="bg-amber-50 dark:bg-amber-950/20 border-amber-200 dark:border-amber-900">
                    <AlertCircle className="h-4 w-4 text-amber-600 dark:text-amber-400" />
                    <AlertDescription className="text-sm text-amber-800 dark:text-amber-300">
                      <strong>Note:</strong> As we're in development, you may encounter occasional issues or bugs. We appreciate your patience and feedback!
                    </AlertDescription>
                  </Alert>
                </div>

                <div className="pt-4 space-y-3">
                  <p className="text-foreground font-medium">Need help or want to report an issue?</p>
                  <div className="flex items-center justify-center gap-3">
                    <div className="p-2 rounded-lg bg-green-100 dark:bg-green-900/30">
                      <Mail className="h-5 w-5 text-green-600 dark:text-green-400" />
                    </div>
                    <div className="text-left">
                      <p className="text-sm text-muted-foreground">Email us at</p>
                      <a 
                        href="mailto:support@fintrack.app" 
                        className="text-lg font-semibold text-primary hover:underline"
                      >
                        support@fintrack.app
                      </a>
                    </div>
                  </div>
                  <p className="text-xs text-muted-foreground">
                    We typically respond within 24-48 hours
                  </p>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default Support;
