'use client';

import React, { useState } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Slider } from '@/components/ui/slider';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Loader2, Upload, Search, RefreshCw } from 'lucide-react';

const formatFileSize = (bytes) => {
  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  let size = bytes;
  let unitIndex = 0;

  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024;
    unitIndex++;
  }

  return `${size.toFixed(2)} ${units[unitIndex]}`;
};

const DocumentCard = ({ document }) => {
  return (
    <Card className="mb-4">
      <CardHeader>
        <CardTitle className="text-lg">📄 {document.filename}</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-3 gap-4">
          <div>
            <h4 className="font-medium mb-2">File Details</h4>
            <p>Size: {formatFileSize(document.file_size)}</p>
            <p>Type: {document.file_type}</p>
            <p>Pages: {document.pages.join(', ')}</p>
          </div>
          <div>
            <h4 className="font-medium mb-2">Dates</h4>
            <p>Created: {document.creation_date}</p>
            <p>Modified: {document.last_modified_date}</p>
          </div>
          <div>
            <h4 className="font-medium mb-2">Storage</h4>
            <p>Path: {document.file_path}</p>
          </div>
        </div>

        <div className="mt-4">
          <h4 className="font-medium mb-2">Content Previews</h4>
          <div className="space-y-2">
            {document.text_chunks.map((chunk, index) => (
              <div key={index} className="border rounded p-4">
                <p className="font-medium mb-2">Page {chunk.page}</p>
                <p className="text-sm">{chunk.text}</p>
              </div>
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  );
};

const RAGDashboard = () => {
  const [activeTab, setActiveTab] = useState('upload');
  const [files, setFiles] = useState([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [documents, setDocuments] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [numResults, setNumResults] = useState(5);
  const [searchResults, setSearchResults] = useState([]);
  const [isSearching, setIsSearching] = useState(false);

  const handleFileChange = (event) => {
    setFiles(Array.from(event.target.files));
  };

  const handleUpload = async () => {
    setIsProcessing(true);
    try {
      const formData = new FormData();
      files.forEach(file => formData.append('files', file));

      const response = await fetch('http://localhost:56165/index/', {
        method: 'POST',
        body: formData
      });

      if (!response.ok) throw new Error('Upload failed');

      setFiles([]);
      setActiveTab('documents');
    } catch (error) {
      console.error('Upload error:', error);
    } finally {
      setIsProcessing(false);
    }
  };

  const fetchDocuments = async () => {
    setIsLoading(true);
    try {
      const response = await fetch('your-fastapi-endpoint/documents');
      const data = await response.json();
      setDocuments(data);
    } catch (error) {
      console.error('Fetch error:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSearch = async () => {
    if (!searchQuery.trim()) return;

    setIsSearching(true);
    try {
      const response = await fetch('your-fastapi-endpoint/search', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          query: searchQuery,
          limit: numResults
        })
      });

      const results = await response.json();
      setSearchResults(results);
    } catch (error) {
      console.error('Search error:', error);
    } finally {
      setIsSearching(false);
    }
  };

  return (
    <div className="container mx-auto p-6">
      <h1 className="text-3xl font-bold mb-6">📚 Genezio RAG</h1>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="mb-4">
          <TabsTrigger value="upload">Upload Documents</TabsTrigger>
          <TabsTrigger value="documents">Indexed Documents</TabsTrigger>
          <TabsTrigger value="search">Search</TabsTrigger>
        </TabsList>

        <TabsContent value="upload">
          <Card>
            <CardContent className="pt-6">
              <Input
                type="file"
                accept=".pdf"
                multiple
                onChange={handleFileChange}
                className="mb-4"
              />

              {files.length > 0 && (
                <div className="mb-4">
                  <h3 className="font-medium mb-2">Selected files:</h3>
                  {files.map((file, index) => (
                    <p key={index}>📄 {file.name}</p>
                  ))}
                </div>
              )}

              <Button
                onClick={handleUpload}
                disabled={!files.length || isProcessing}
              >
                {isProcessing ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Processing...
                  </>
                ) : (
                  <>
                    <Upload className="mr-2 h-4 w-4" />
                    Process and Index Documents
                  </>
                )}
              </Button>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="documents">
          <div className="mb-4">
            <Button onClick={fetchDocuments} disabled={isLoading}>
              {isLoading ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <RefreshCw className="mr-2 h-4 w-4" />
              )}
              Refresh
            </Button>
          </div>

          {documents.length === 0 ? (
            <Alert>
              <AlertDescription>
                No documents have been indexed yet.
              </AlertDescription>
            </Alert>
          ) : (
            documents.map((doc, index) => (
              <DocumentCard key={index} document={doc} />
            ))
          )}
        </TabsContent>

        <TabsContent value="search">
          <Card>
            <CardContent className="pt-6">
              <div className="space-y-4">
                <Input
                  placeholder="Enter your search query"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                />

                <div>
                  <p className="mb-2">Number of results: {numResults}</p>
                  <Slider
                    value={[numResults]}
                    onValueChange={([value]) => setNumResults(value)}
                    min={1}
                    max={20}
                    step={1}
                  />
                </div>

                <Button
                  onClick={handleSearch}
                  disabled={!searchQuery.trim() || isSearching}
                >
                  {isSearching ? (
                    <>
                      <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      Searching...
                    </>
                  ) : (
                    <>
                      <Search className="mr-2 h-4 w-4" />
                      Search
                    </>
                  )}
                </Button>

                {searchResults.length > 0 && (
                  <div className="mt-6 space-y-4">
                    {searchResults.map((result, index) => (
                      <Card key={index}>
                        <CardContent className="pt-6">
                          <p>{result}</p>
                        </CardContent>
                      </Card>
                    ))}
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default RAGDashboard;