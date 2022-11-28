<script>
    import { onMount, onDestroy } from 'svelte'
    import { interpret } from 'xstate'
  
    import infiniteScrollMachine from '../js/scroll'
  
    import Footer from './Footer.svelte'
    
    let options = {
      root: document.getElementById('scrollArea'),
      rootMargin: '0px',
      threshold: 0.5,
    }
  
    const machine = infiniteScrollMachine
    const service = interpret(machine).start()
  
    let observer = new IntersectionObserver(event => {
      const [entries] = event
      if (entries.isIntersecting) {
        service.send({ type: 'SCROLL_TO_BOTTOM' })
      }
    }, options)
  
    onMount(() => {
      service.send({ type: 'INITIATE_DATA' })
      observer.observe(document.querySelector('footer'))
    })
    onDestroy(() => {
      observer.unobserve(document.querySelector('footer'))
    })
  </script>


<div class="page-wrapper">
    {#if $service.matches('checkingIfThereIsMoreData') || $service.matches('loadMoreData')}
    {#each $service.context.data as toot}
    {#if toot.reblog}
        <div class="toot">
            <div class="row reference">
                <p>Reblog by
                    <strong>{toot.account.username}</strong>
                </p>
            </div>
            <div class="row">
                <div class="column-1">
                    <div class="avatar">
                        <img src="{toot.reblog.account.avatar}" alt="avatar">
                    </div>
                </div>
                <div class="column-9">
                    <div class="content">
                        <strong>{toot.reblog.account.username}</strong> <small>{toot.reblog.account.acct}</small> <small>{toot.reblog.created_at}</small>
                        {@html toot.reblog.content}
                    </div>
                </div>
            </div>
        </div>
    {:else}
        <div class="toot">
            <div class="row">
                <div class="column-1">
                    <div class="avatar">
                        <img src="{toot.account.avatar}" alt="avatar">
                    </div>
                </div>
                <div class="column-9">
                    <div class="content">
                        <strong>{toot.account.username}</strong> <small>{toot.account.acct}</small> <small>{toot.created_at}</small>
                        {@html toot.content}
                    </div>
                </div>
            </div>
        </div>
    {/if}

    <!-- {:else}
        <p>No toots</p> -->
    {/each}


{/if}

<Footer />

</div> 