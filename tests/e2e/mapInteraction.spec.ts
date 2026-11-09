import { test, expect, type Page } from '@playwright/test'
import { mockMapTiles } from '../mapTiles'
import type { Snapshot, ReceptionSpot } from '../../src/types'

async function mapFixture(page: Page) {
 const now = Date.UTC(2026, 10, 8, 12)
 const spot: ReceptionSpot = { sender:'N0CALL',receiver:'K1FOCUS',grid:'RJ90',band:'20m',mode:'FT8',snr:-12,frequency:14074000,heardAt:now-60000 }
 const snapshot: Snapshot = { epoch:'map-interaction',revision:1,step:3,call:'K1FOCUS',source:'radio',
  history:[{call:'K1FOCUS',rigId:'A',stationCall:'N0CALL',dxGrid:'RJ90',band:'20m',mode:'FT8',selectedAt:now,recency:1}],rigs:[],
  counters:{decodes:1,malformed:0},receiver:{status:'listening',error:null},preferences:{title:'Map interaction · fictional reports',appearance:'dark',radioStrip:false},
  pskreporter:{config:{enabled:true,callsign:'',window_minutes:15},status:'connected',error:'',callsigns:['N0CALL'],connectedAt:now,evicted:0,spots:[spot,{...spot,receiver:'K2NEAR',grid:'AJ00'}]},
  localReceptions:{evicted:0,spots:[{call:'K2NEAR',stationCall:'N0CALL',rigId:'A',band:'20m',mode:'FT8',snr:-14,grid:'AJ00',heardAt:now-120000}]} }
 await page.clock.install({time:now}); await mockMapTiles(page)
 await page.addInitScript(()=>{
  window.EventSource=class {
   static CLOSED=2;readyState=1;onopen?:()=>void
   constructor(){setTimeout(()=>this.onopen?.(),25)}
   addEventListener(_name:string,callback:(event:{data:string})=>void){window.addEventListener('map-fixture',event=>callback({data:JSON.stringify((event as CustomEvent).detail)}))}
   close(){this.readyState=2}
  } as unknown as typeof EventSource
 })
 await page.route('**/api/**',route=>route.fulfill({contentType:'application/json',body:JSON.stringify(snapshot)}))
 await page.goto('/')
 await expect(page.locator('.station-map-canvas')).toHaveAttribute('data-basemap-state','ready')
 await expect(page.locator('.station-map-reception')).toHaveCount(2)
 return async()=>{
  snapshot.pskreporter!.spots[1]!.heardAt+=100
  snapshot.revision++
  await page.evaluate(data=>window.dispatchEvent(new CustomEvent('map-fixture',{detail:data})),snapshot)
  await expect.poll(()=>page.locator('.station-map-reception[data-direction=both]').getAttribute('aria-label')).toContain(new Date(snapshot.pskreporter!.spots[1]!.heardAt).toISOString())
 }
}

test('focused label stays horizontal and multiline reception details have readable width', async({page})=>{
 await mapFixture(page)
 const label=page.locator('.leaflet-tooltip').getByText('K1FOCUS',{exact:true})
 const bounds=await label.boundingBox()
 expect(bounds!.width).toBeGreaterThan(bounds!.height*2)
 await page.locator('.station-map-reception[data-direction=both]').focus()
 const details=page.locator('.leaflet-tooltip').filter({hasText:'Mutual reception'})
 await expect(details).toBeVisible()
 const detailBounds=await details.boundingBox()
 expect(detailBounds!.width).toBeGreaterThan(200)
 expect(detailBounds!.height).toBeLessThan(220)
 await page.locator('.station-map').screenshot({path:'test-results/map-readable-labels.png'})
 await page.setViewportSize({width:320,height:700})
 const narrow=(await label.boundingBox())!
 expect(narrow.width).toBeGreaterThan(narrow.height*2)
 await expect.poll(async()=> (await details.boundingBox())!.width).toBeLessThan(270)
})

test('stations remain on the visible world during repeated east/west drags', async({page})=>{
 const update=await mapFixture(page)
 const errors:string[]=[];page.on('pageerror',error=>errors.push(error.message))
 const canvas=page.locator('.station-map-canvas'), pin=page.locator('.station-map-pin')
 const zoomOut=page.getByRole('button',{name:'Zoom out station map',exact:true})
 for(const zoom of [3,2]) { await zoomOut.click(); await expect(canvas).toHaveAttribute('data-zoom',String(zoom)) }
 await expect(canvas).toHaveAttribute('data-zoom','2')
 await page.waitForTimeout(300)
 const area=(await canvas.boundingBox())!
 expect(area.width).toBeGreaterThan(1024) // At zoom 2, one whole world fits inside this canvas.
 const samples:{pinX:number;nearX:number;aligned:number;gridAligned:number}[]=[]
 for(const direction of [1,-1]) {
  for(let pass=0;pass<3;pass++) {
   const start=area.x+area.width*(direction===1?.12:.88), end=area.x+area.width*(direction===1?.88:.12), y=area.y+area.height*.8
   await page.mouse.move(start,y);await page.mouse.down()
   for(let step=1;step<=12;step++) {
    await page.mouse.move(start+(end-start)*step/12,y)
    samples.push(await canvas.evaluate(node=>{
     const focus=node.querySelector('.station-map-pin')!.getBoundingClientRect(), heard=node.querySelector('.station-map-reception[data-direction=sent]')!.getBoundingClientRect(), near=node.querySelector('.station-map-reception[data-direction=both]')!.getBoundingClientRect(), grid=node.querySelector('.station-map-grid')!.getBoundingClientRect(), map=node.getBoundingClientRect()
     return {pinX:focus.x+focus.width/2-map.x,nearX:near.x+near.width/2-map.x,aligned:Math.abs(focus.x+focus.width/2-heard.x-heard.width/2),gridAligned:Math.abs(focus.x+focus.width/2-grid.x-grid.width/2)}
    }))
   }
   await page.mouse.up();await page.waitForTimeout(250)
   await update() // Stream updates must keep the current visible world too.
  }
 }
 expect(samples.filter(s=>s.pinX<0||s.pinX>area.width||s.nearX<0||s.nearX>area.width)).toEqual([])
 expect(samples.every(s=>s.aligned<2)).toBe(true)
 expect(samples.find(s=>s.gridAligned>=2)).toBeUndefined()
 await expect(pin).toHaveAttribute('data-outlook-score','90')
 await page.getByRole('button',{name:'Center station',exact:true}).click()
 await expect.poll(async()=>{const box=(await pin.boundingBox())!,map=(await canvas.boundingBox())!;return Math.abs(box.x+box.width/2-map.x-map.width/2)}).toBeLessThan(3)
 expect(errors).toEqual([])
})
