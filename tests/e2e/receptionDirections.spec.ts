import { test, expect } from '@playwright/test'
import { mockMapTiles } from '../mapTiles'
import type { LocalReceptionSpot, ReceptionSpot, Snapshot } from '../../src/types'

test('reception directions preserve outlook, context, map view and a bounded scrolling popup', async ({ page }) => {
 const now = Date.UTC(2026, 10, 8, 12)
 const sent: ReceptionSpot = { sender:'N0CALL', receiver:'K1FOCUS', grid:'FN31', band:'20m', mode:'FT8', frequency:14074000, snr:-19, heardAt:now-32*60000 }
 const local: LocalReceptionSpot = { call:'K1FOCUS', stationCall:'N0CALL', rigId:'A', grid:'FN31', band:'20m', mode:'FT8', snr:-14, heardAt:now-2*60000 }
 const snapshot: Snapshot = { epoch:'directions-fixture', revision:1, step:3, call:'K1FOCUS', source:'radio',
  history:[{call:'K1FOCUS',rigId:'A',stationCall:'N0CALL',dxGrid:'FN31',band:'20m',mode:'FT8',selectedAt:now,recency:1}], rigs:[],
  counters:{packets:10,decodes:8,malformed:0}, receiver:{status:'listening',error:null}, preferences:{title:'Reception directions · fictional reports',appearance:'dark',radioStrip:false},
  pskreporter:{config:{enabled:true,callsign:'',window_minutes:15},status:'connected',error:'',callsigns:['N0CALL'],connectedAt:now,evicted:0,
   spots:[sent,...['K2MUTUAL','K4SENT','K5SAMEGRID'].map((receiver,i)=>({...sent,receiver,grid:['FN32','FN30','FN33'][i]!,heardAt:now-2*60000}))]},
  localReceptions:{evicted:0,spots:[local,...['K2MUTUAL','K3LOCAL','K6DIFFERENT'].map((call,i)=>({...local,call,grid:['FN32','FN34','FN33'][i]!})),
   {...local,call:'K7RIGB',rigId:'B'}, {...local,call:'K8IDENTITY',stationCall:'N0CALL/P'}, {...local,call:'K9BAND',band:'17m'},
   {...local,call:'K9OLD',heardAt:now-20*60000}, {...local,call:'K9BAD',grid:'ZZ99'}]} }
 const errors: string[] = []; page.on('pageerror', error=>errors.push(error.message))
 await page.clock.install({time:now}); await mockMapTiles(page)
 await page.addInitScript(()=>{
  window.EventSource = class {
   static CLOSED=2; readyState=1; onopen?:()=>void
   constructor(){setTimeout(()=>this.onopen?.(),25)}
   addEventListener(_name:string,callback:(event:{data:string})=>void){window.addEventListener('direction-fixture',event=>callback({data:JSON.stringify((event as CustomEvent).detail)}))}
   close(){this.readyState=2}
  } as unknown as typeof EventSource
 })
 await page.route('**/api/**',route=>route.fulfill({contentType:'application/json',body:JSON.stringify(snapshot)}))
 await page.goto('/')
 const push=async()=>{snapshot.revision++;await page.evaluate(data=>window.dispatchEvent(new CustomEvent('direction-fixture',{detail:data})),snapshot)}
 const pin=page.locator('.station-map-pin'), dots=page.locator('.station-map-reception'), selector=page.getByRole('group',{name:'Reception direction'})
 const button=(name:string)=>selector.getByRole('button',{name,exact:true})
 const station=(call:string)=>dots.filter({has:page.locator('span')}).and(page.locator(`[aria-label*="${call}"]`))
 await expect(button('Heard me')).toHaveAttribute('aria-pressed','true')
 await expect(dots).toHaveCount(4) // Three upstream stations plus independent focused local evidence.
 await expect(station('K3LOCAL')).toHaveCount(0)
 await expect(pin).toHaveAttribute('data-direction','recv')
 await expect(pin).toHaveAttribute('data-outlook-score','60')
 await expect(station('K2MUTUAL')).toHaveAttribute('data-direction','both')
 const transform=await pin.getAttribute('style'), zoom=await page.locator('.station-map-canvas').getAttribute('data-zoom')
 await button('Both').click(); await expect(dots).toHaveCount(6)
 await expect(station('K5SAMEGRID')).toHaveAttribute('data-direction','sent')
 await expect(station('K6DIFFERENT')).toHaveAttribute('data-direction','recv')
 await expect(station('K3LOCAL')).toHaveAttribute('aria-label',/N0CALL heard K3LOCAL.*-14 dB/)
 expect(await station('K3LOCAL').locator('span').evaluate(node=>getComputedStyle(node).backgroundColor)).toBe('rgb(52, 120, 212)')
 expect(await station('K4SENT').locator('span').evaluate(node=>getComputedStyle(node).backgroundColor)).toBe('rgb(240, 161, 43)')
 expect(await station('K2MUTUAL').locator('span').evaluate(node=>getComputedStyle(node).backgroundImage)).toContain('linear-gradient')
 await expect(station('K2MUTUAL')).toHaveAttribute('aria-label',/Mutual reception[\s\S]*K2MUTUAL heard N0CALL[\s\S]*N0CALL heard K2MUTUAL/)
 await button('I heard').click(); await expect(dots).toHaveCount(4)
 await expect(pin).toHaveAttribute('data-outlook-score','60')
 expect(await pin.getAttribute('style')).toBe(transform)
 expect(await page.locator('.station-map-canvas').getAttribute('data-zoom')).toBe(zoom)
 await page.getByLabel('Reception time window').selectOption('60')
 await expect(pin).toHaveAttribute('data-direction','both')
 await button('Both').click()
 await pin.click({position:{x:2,y:12}})
 const popup=page.getByRole('dialog',{name:'QSO Outlook details for K1FOCUS'})
 await expect(popup).toContainText('Reception: Mutual reception')
 await expect(popup).toContainText('Map display: last 60 min · Outlook: 15 min')
 await expect(popup).toContainText('Last heard you: 32 minutes ago')
 await expect(popup).toContainText('outside 15-minute Outlook window')
 await expect(popup).toContainText('Last you heard: 2 minutes ago')
 await expect(page.locator('.leaflet-tooltip:visible')).toHaveCount(0)
 const assertFits=async()=>{
  const box=await popup.boundingBox(), canvas=await page.locator('.station-map-canvas').boundingBox()
  expect(box!.y).toBeGreaterThanOrEqual(canvas!.y)
  expect(box!.y+box!.height).toBeLessThanOrEqual(canvas!.y+canvas!.height-20)
  expect(box!.x+box!.width).toBeLessThanOrEqual(canvas!.x+canvas!.width)
  await expect(popup.getByRole('button',{name:'Close QSO Outlook'})).toBeVisible()
 }
 await assertFits()
 await page.locator('.station-map').screenshot({path:'test-results/reception-directions-dark.png'})
 snapshot.preferences!.appearance='light';await push()
 await page.setViewportSize({width:320,height:640})
 await popup.locator('small').scrollIntoViewIfNeeded()
 await assertFits()
 expect(await popup.locator('.qso-outlook-body').evaluate(node=>node.scrollHeight>node.clientHeight)).toBe(true)
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true)
 await page.locator('.station-map').screenshot({path:'test-results/reception-directions-light-mobile.png'})
 await popup.getByRole('button',{name:'Close QSO Outlook'}).click();await expect(popup).toHaveCount(0)
 // Only an old direct report remains: map confirmation survives while outlook is Unknown.
 snapshot.pskreporter!.spots=[sent];await push()
 await expect(pin).toHaveAttribute('data-outlook-score','unknown')
 await expect(pin).toHaveAttribute('data-direction','both')
 // Rig and operating identity changes cannot reuse the previous receiver's decodes.
 snapshot.history[0]!.rigId='B';await push()
 await expect(station('K3LOCAL')).toHaveCount(0)
 await expect(station('K7RIGB')).toHaveCount(1)
 snapshot.history[0]!.stationCall='N0CALL/P';await push()
 await expect(dots).toHaveCount(0)
 await expect(pin).toBeVisible()
 snapshot.history[0]!.rigId='A';snapshot.history[0]!.stationCall='N0CALL';snapshot.pskreporter!.config.enabled=false;await push()
 await expect(pin).toHaveAttribute('data-direction','recv')
 await expect(pin).toHaveAttribute('data-outlook-score','unknown')
 await button('I heard').click();await expect(station('K3LOCAL')).toHaveCount(1)
 await page.getByLabel('Reception time window').selectOption('5')
 await page.clock.fastForward(4*60000)
 await expect(dots).toHaveCount(0)
 await expect(pin).toBeVisible()
 await expect(pin).toHaveAttribute('data-direction','neutral')
 expect(errors).toEqual([])
})
