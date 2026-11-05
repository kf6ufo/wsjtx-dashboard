import { test, expect } from '@playwright/test'
import { mockMapTiles } from '../mapTiles'

test('reception dots follow focus band and transmitting identity, expire, and preserve map position', async ({ page }) => {
 const now = Date.UTC(2026,10,5,12)
 const spot = { sender:'N0CALL',receiver:'K1FOCUS',grid:'FN31',band:'20m',frequency:14074000,mode:'FT8',snr:-12,heardAt:now-60000 }
 const snapshot = { epoch:'psk-map-fixture', revision:1, step:3, sample:false, call:'K1FOCUS', source:'radio',
  history:[{call:'K1FOCUS',rigId:'Fixture A',stationCall:'N0CALL',dxGrid:'FN31',deGrid:'CN85',band:'20m',mode:'FT8',selectedAt:now,recency:1}],
  rigs:[{id:'Fixture A',name:'Fixture A',stationCall:'N0CALL',call:'K1FOCUS',band:'20m',frequency:14074000,mode:'FT8',online:true,lastSeen:now,color:'#70c9bd'}],
  counters:{packets:5,decodes:3,malformed:0}, receiver:{status:'listening',error:null},
  preferences:{title:'Reception overlay preview · fictional stations',appearance:'dark',radioStrip:false},
  pskreporter:{config:{enabled:true,callsign:'',window_minutes:15},status:'connected',error:'',callsigns:['N0CALL'],connectedAt:now-600000,evicted:0,
   spots:[spot,{...spot,receiver:'K2NEAR',grid:'FN32',mode:'FT4',heardAt:now-120000},{...spot,receiver:'K3OLDER',grid:'FM29',heardAt:now-1200000},{...spot,receiver:'K4BAND',band:'15m'},{...spot,sender:'K5OTHER',receiver:'K6IDENTITY'}]}}
 const errors:string[]=[]; page.on('pageerror', error=>errors.push(error.message))
 await page.clock.install({time:now})
 await mockMapTiles(page)
 await page.addInitScript(() => {
  window.EventSource = class {
   onopen?: () => void
   constructor() { setTimeout(()=>this.onopen?.(), 25) }
   addEventListener(_name: string, callback: (event: { data: string }) => void) {
    window.addEventListener('psk-fixture', event=>callback({data:JSON.stringify((event as CustomEvent).detail)}))
   }
   close() {}
  } as unknown as typeof EventSource
 })
 await page.route('**/api/**', route=>route.fulfill({contentType:'application/json',body:JSON.stringify(snapshot)}))
 await page.goto('/')
 await expect(page.locator('.station-map-canvas')).toHaveAttribute('data-basemap-state','ready')
 await expect(page.locator('.station-map-reception')).toHaveCount(2)
 await expect(page.locator('.station-map')).toContainText('K1FOCUS heard you 1 min ago')
 const focus=page.locator('.station-map-pin'), heard=page.locator('.station-map-reception[aria-label^="K1FOCUS heard"]')
 const a=await focus.boundingBox(), b=await heard.boundingBox()
 expect(b!.width).toBeLessThan(a!.width)
 expect(Math.abs((a!.x+a!.width/2)-(b!.x+b!.width/2))).toBeLessThan(2)
 expect(Math.abs((a!.y+a!.height/2)-(b!.y+b!.height/2))).toBeLessThan(2)
 await page.getByLabel('Reception time window').selectOption('60')
 await expect(page.locator('.station-map-reception')).toHaveCount(3)
 await page.locator('.station-map').screenshot({path:'test-results/pskreporter-map-dark.png'})
 // Drag the map, then stream another report. It must leave the operator's view alone.
 const canvas=await page.locator('.station-map-canvas').boundingBox()
 await page.mouse.move(canvas!.x+canvas!.width/2,canvas!.y+canvas!.height/2)
 await page.mouse.down();await page.mouse.move(canvas!.x+canvas!.width/2+90,canvas!.y+canvas!.height/2+40,{steps:10});await page.mouse.up()
 await page.waitForTimeout(500)
 const transform=await focus.getAttribute('style')
 snapshot.revision++; snapshot.pskreporter.spots.push({...spot,receiver:'K7NEW',grid:'FN30',heardAt:now})
 await page.evaluate(data=>window.dispatchEvent(new CustomEvent('psk-fixture',{detail:data})),snapshot)
 await expect(page.locator('.station-map-reception')).toHaveCount(4)
 expect(await focus.getAttribute('style')).toBe(transform)
 // A local time-window change uses the collected cache without HTTP or MQTT queries.
 await page.getByLabel('Reception time window').selectOption('5')
 await page.clock.fastForward(6*60000)
 await expect(page.locator('.station-map-reception')).toHaveCount(0)
 await page.getByLabel('Reception time window').selectOption('60')
 await expect(page.locator('.station-map-reception')).toHaveCount(4)
 snapshot.revision++;snapshot.history[0]!.band='15m'
 await page.evaluate(data=>window.dispatchEvent(new CustomEvent('psk-fixture',{detail:data})),snapshot)
 await expect(page.locator('.station-map-reception')).toHaveCount(1)
 await expect(page.locator('.station-map')).not.toContainText('inner amber dot')
 snapshot.revision++;snapshot.history[0]!.band='20m';snapshot.history[0]!.stationCall='K5OTHER'
 snapshot.preferences.appearance='light'
 await page.evaluate(data=>window.dispatchEvent(new CustomEvent('psk-fixture',{detail:data})),snapshot)
 await expect(page.locator('.station-map-reception')).toHaveCount(1)
 await expect(page.locator('.station-map-reception')).toHaveAttribute('aria-label',/^K6IDENTITY heard K5OTHER/)
 await page.setViewportSize({width:390,height:844})
 await page.getByRole('button',{name:'Center station',exact:true}).click()
 await page.locator('.station-map').screenshot({path:'test-results/pskreporter-map-light-mobile.png'})
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true)
 await page.getByRole('button',{name:'Settings',exact:true}).click()
 await page.getByRole('tab',{name:'PSKReporter',exact:true}).click()
 await expect(page.getByRole('form',{name:'PSKReporter settings'})).toBeVisible()
 expect(errors).toEqual([])
})
