
import { assign, createMachine } from 'xstate'
import { getHomeTimeline } from './timelines'


const URL = "http://localhost:8888"
const ACCES_TOKEN = "dummy"


const infiniteScrollMachine = createMachine({
  id: 'infiniteScroll',
  context: {},
  initial: 'idle',
  states: {
    idle: {
      exit: ['clearErrorMessage'],
      on: {
        SCROLL_TO_BOTTOM: 'fetchingRowOfData',
        INITIATE_DATA: {
          target: 'checkingIfThereIsMoreData',
          actions: ['initDataContext'],
        },
      },
    },
    fetchingRowOfData: {
      invoke: {
        src: 'fetchRowOfData',
        onError: {
          target: 'idle',
          actions: 'assignErrorMessageToContext',
        },
      },
    },
    loadMoreData: {
      invoke: {
        src: 'fetchRowOfData',
        onDone: {
          target: 'checkingIfThereIsMoreData',
          actions: 'assignDataToContext',
        },
        onError: {
          target: 'noMoreDataToFetch',
          actions: 'setError',
        },
      },
    },
    checkingIfThereIsMoreData: {
      on: {
        SCROLL_TO_BOTTOM: {
          target: 'loadMoreData',
          cond: 'thereIsMoreData',
        },
      },
    },
    noMoreDataToFetch: {
      type: 'final',
    },
  },
}, {
  guards: {
    thereIsMoreData: (context) => {
      return context.totalEntries > context.data.length;
    },
  },
  services: {
    fetchRowOfData: () => async () =>  {
      const data = await getHomeTimeline(URL, ACCES_TOKEN)
      return {"toots": data, "totalEntries": 80}
    },
  },
  actions: {
    initDataContext: assign((context, event) => {
      return {
        data: [],
        totalEntries: Infinity,
      }
    }),
    assignDataToContext: assign((context, event) => {
      return {
        data: [...context.data, ...event.data.toots],
        totalEntries: event.data.totalEntries,
      };
    }),
    clearErrorMessage: assign((context) => ({
      errorMessage: undefined,
    })),
    assignErrorMessageToContext: assign((context, event) => {
      return {
        errorMessage: event.data?.message || 'An unknown error occurred',
      };
    }),
  },
})

export default infiniteScrollMachine