import React from 'react';
import ReactDOM from 'react-dom/client';
import { DirectionProvider, MantineProvider, createTheme } from '@mantine/core';
import { Notifications } from '@mantine/notifications';
import '@mantine/core/styles.css';
import '@mantine/notifications/styles.css';
import './styles.css';
import App from './App';

const theme = createTheme({
  primaryColor: 'indigo',
  fontFamily: 'Vazirmatn, Tahoma, sans-serif',
  defaultRadius: 'md',
});

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <DirectionProvider initialDirection="rtl">
      <MantineProvider theme={theme}>
        <Notifications position="top-left" />
        <App />
      </MantineProvider>
    </DirectionProvider>
  </React.StrictMode>,
);
