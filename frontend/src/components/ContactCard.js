import React from 'react';
import { Card, CardContent, Typography, Link, Box } from '@mui/material';

export const ContactCard = ({ contact }) => {
  if (!contact) return null;

  return (
    <Card sx={{ minWidth: 300, maxWidth: 400, margin: 2, boxShadow: 3 }}>
      <CardContent>
        <Typography variant="h6" gutterBottom>
          {contact.name}
        </Typography>
        <Typography color="textSecondary" variant="body2">
          <b>ID:</b> {contact.id}
        </Typography>
        <Typography color="textSecondary" variant="body2">
          <b>Type:</b> {contact.type}
        </Typography>
        {contact.creation_time && (
          <Typography color="textSecondary" variant="body2">
            <b>Created:</b> {new Date(contact.creation_time).toLocaleString()}
          </Typography>
        )}
        {contact.last_modified_time && (
          <Typography color="textSecondary" variant="body2">
            <b>Last Modified:</b> {new Date(contact.last_modified_time).toLocaleString()}
          </Typography>
        )}
        <Typography color="textSecondary" variant="body2">
          <b>Visibility:</b> {contact.visibility ? 'Visible' : 'Hidden'}
        </Typography>
        {contact.url && (
          <Box mt={1}>
            <Link href={contact.url} target="_blank" rel="noopener">
              View in HubSpot
            </Link>
          </Box>
        )}
      </CardContent>
    </Card>
  );
};