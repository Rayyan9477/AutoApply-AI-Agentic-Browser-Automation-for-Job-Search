import { setupServer } from 'msw/node';
import { handlers } from './handlers';

/** MSW server instance for intercepting API requests in tests. */
export const server = setupServer(...handlers);
