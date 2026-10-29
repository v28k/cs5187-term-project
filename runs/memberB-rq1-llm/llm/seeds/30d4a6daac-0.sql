SELECT XMLSERIALIZE(CONTENT XMLPARSE(CONTENT '<?xml version="1.0"?>' || chr(65279) || 'abc') AS text INDENT);
