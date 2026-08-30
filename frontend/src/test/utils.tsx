import { ReactElement, ReactNode } from "react";
import { render, RenderOptions } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, MemoryRouter } from "react-router-dom";

// Create a fresh QueryClient for each test
function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
        staleTime: 0,
      },
      mutations: {
        retry: false,
      },
    },
  });
}

interface WrapperProps {
  children: ReactNode;
}

interface CustomRenderOptions extends Omit<RenderOptions, "wrapper"> {
  queryClient?: QueryClient;
  withRouter?: boolean;
  /** Render inside a MemoryRouter seeded with these entries, instead of a BrowserRouter. */
  initialEntries?: string[];
}

/**
 * Custom render function that wraps components with necessary providers
 */
function customRender(
  ui: ReactElement,
  options: CustomRenderOptions = {},
): ReturnType<typeof render> & { queryClient: QueryClient } {
  const {
    queryClient = createTestQueryClient(),
    withRouter = true,
    initialEntries,
    ...renderOptions
  } = options;

  function Wrapper({ children }: WrapperProps) {
    let content = (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );

    if (withRouter) {
      content = initialEntries ? (
        <MemoryRouter initialEntries={initialEntries}>{content}</MemoryRouter>
      ) : (
        <BrowserRouter>{content}</BrowserRouter>
      );
    }

    return content;
  }

  const renderResult = render(ui, { wrapper: Wrapper, ...renderOptions });

  return {
    ...renderResult,
    queryClient,
  };
}

// Re-export everything from testing-library
export * from "@testing-library/react";
export { userEvent } from "@testing-library/user-event";
export { customRender as render };
export { createTestQueryClient };
