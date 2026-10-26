import {test,expect} from '@playwright/test'
import{execFileSync}from'node:child_process'
import{mockMapTiles}from'../mapTiles'
test('saved connection resolves both radios and one exact queued contact without enabling logging',async({page,browser,request,baseURL})=>{
 const second=await browser.newPage(),errors:string[]=[]
 await mockMapTiles(page);await mockMapTiles(second);page.on('pageerror',e=>errors.push(e.message));second.on('pageerror',e=>errors.push(e.message))
 execFileSync('.venv/bin/python',['-c',"import socket\nfrom backend.tests.fixtures import status,text\ns=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)\nfor rig in ['IC7300','IC9100']:s.sendto(status(call='K0BASE',rig=rig).replace(text('N0TEST'),text('KF6UFO')),('127.0.0.1',18244))"])
 await page.goto(baseURL!);await second.goto(baseURL!);await page.getByRole('button',{name:'Settings',exact:true}).click();await page.getByRole('tab',{name:'Wavelog connection',exact:true}).click()
 await page.getByRole('button',{name:'Test saved connection & load locations',exact:true}).click()
 const mapping=page.getByRole('tabpanel').locator('.station-associations')
 await expect(mapping).toContainText('IC7300');await expect(mapping).toContainText('IC9100');await expect(mapping.locator('tbody tr')).toHaveCount(2)
 await expect(mapping.locator('tbody tr').first()).toContainText('ID 1');await expect(mapping.locator('tbody tr').nth(1)).toContainText('ID 1')
 await page.getByRole('tab',{name:'QSO history & logging',exact:true}).click()
 await expect(page.getByLabel('Station callsign',{exact:true})).toHaveCount(0)
 await expect(page.getByLabel('Enable completed-QSO logging',{exact:true})).not.toBeChecked()
 await page.getByLabel('IC7300 · location override',{exact:true}).selectOption('1')
 await page.getByRole('button',{name:'Save history and logging settings',exact:true}).click();await expect(mapping.locator('tbody tr').first()).toContainText('Explicit override')
 const before=(await(await request.get('/api/snapshot')).json()).qso.queue
 const job=before.recent.find((j:any)=>j.contact?.CALL==='K1MATCH'),missing=before.recent.find((j:any)=>j.contact?.CALL==='K2MISS')
 const card=page.locator(`[data-job-id="${job.id}"]`),other=page.locator(`[data-job-id="${missing.id}"]`)
 await expect(card).toContainText('2026-10-26 18:51:00 UTC');await card.getByLabel('Location for exact verification').selectOption('1');await card.getByRole('button',{name:'Resolve as already logged',exact:true}).click()
 await expect(card).toContainText('Resolved externally');await expect(card).toContainText('receipt 44')
 await expect(other).not.toContainText('Resolved externally')
 await other.getByLabel('Location for exact verification').selectOption('1');await other.getByRole('button',{name:'Resolve as already logged',exact:true}).click();await expect(other).toContainText('No exact existing QSO')
 await second.getByRole('button',{name:'Settings',exact:true}).click();await second.getByRole('tab',{name:'QSO history & logging',exact:true}).click();await expect(second.locator(`[data-job-id="${job.id}"]`)).toContainText('Resolved externally')
 const after=(await(await request.get('/api/snapshot')).json()).qso
 expect(after.config.logging_enabled).toBe(false);expect(after.config.log_to_wavelog).toBe(false)
 expect(after.queue.destinations).toContainEqual({destination:'adif',status:'delivered',count:2})
 expect(after.queue.destinations).toContainEqual({destination:'wavelog',status:'held',count:1})
 await page.screenshot({path:'test-results/mapping-recovery-desktop.png',fullPage:true});await page.setViewportSize({width:390,height:844});expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true)
 expect(errors).toEqual([]);await second.close()
})
